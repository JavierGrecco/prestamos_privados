"""
Conexión a SQLite con configuración financiera.

Este módulo encapsula TODO lo relacionado con abrir, configurar,
usar y cerrar la base de datos. La idea es que ninguna otra parte
del sistema sepa que existe SQLite: si mañana migramos a PostgreSQL,
solo se cambia este archivo.

## Decisiones importantes

### ¿Por qué SQLite y no PostgreSQL?
Para una aplicación local y familiar, SQLite es perfecto:
  - Un solo archivo, cero configuración de servidor.
  - Backups triviales (copiar el archivo).
  - Sin dependencias externas.
  - Durabilidad ACID completa.
Si en el futuro se necesita multiusuario en la nube, se puede
migrar manteniendo el mismo código de dominio.

### ¿Por qué WAL y no el journal por defecto?
WAL (Write-Ahead Logging) permite que las lecturas no bloqueen a
las escrituras y viceversa. En una app con lecturas frecuentes
(dashboards) y escrituras puntuales (pagos), esto mejora mucho la
experiencia. Además, con synchronous=FULL, mantiene la durabilidad
ante cortes de energía.

### ¿Por qué synchronous=FULL y no NORMAL?
FULL garantiza que cada COMMIT se escribe al disco antes de
retornar. Es más lento (una fracción de milisegundo por escritura)
pero garantiza que un corte de energía no pierda datos. Para una
app financiera, la durabilidad vale más que la velocidad.

### ¿Por qué verificar integridad al abrir?
Porque es la única forma de detectar tempranamente si algo se
corrompió. Si una base pasa la verificación, sabés que podés
operar sobre ella. Si no, mejor fallar rápido que corromper más.

### ¿Por qué las transacciones son reentrantes?
Porque un servicio de aplicación puede necesitar abrir una
transacción que abarca varias operaciones, y cada operación a su
vez puede necesitar su propia transacción. Si no fueran
reentrantes, SQLite tiraría el error "cannot start a transaction
within a transaction".

La solución es contar la profundidad: solo la transacción más
externa hace BEGIN/COMMIT/ROLLBACK. Las internas se "adhieren" a
la existente.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .excepciones import (
    ErrorConexion,
    ErrorIntegridad,
    ErrorTransaccion,
)


class BaseDatos:
    """
    Envuelve una conexión a SQLite con la configuración correcta.

    Uso típico:
        db = BaseDatos("datos/prestamos.db")
        db.abrir()
        try:
            with db.transaccion():
                db.ejecutar("INSERT INTO ...", params)
        finally:
            db.cerrar()

    O más simple, usando el context manager:
        with BaseDatos("datos/prestamos.db") as db:
            with db.transaccion():
                db.ejecutar("INSERT INTO ...", params)

    La conexión se cierra automáticamente al salir del with.

    Las transacciones son reentrantes: si un método abre una
    transacción y llama a otro que también abre, la interna se
    une a la externa. Solo la más externa hace COMMIT o ROLLBACK.
    """

    def __init__(self, ruta: str | Path):
        """
        Prepara la base de datos pero no la abre todavía.

        Parámetros:
            ruta: ubicación del archivo .db. Si no existe, se crea
                al llamar a abrir().
        """
        self.ruta = Path(ruta)
        self._conexion: sqlite3.Connection | None = None
        # Contador de profundidad de transacciones. Cuando es 0,
        # no hay transacción activa. Cuando es >0, estamos dentro
        # de una o más transacciones anidadas.
        self._profundidad_transaccion: int = 0

    # ============================================================
    # Ciclo de vida
    # ============================================================

    def abrir(self) -> None:
        """
        Abre la conexión y aplica la configuración.

        Si la base no existe, SQLite la crea automáticamente.
        Después de configurar los PRAGMAs, se corre una verificación
        de integridad rápida para detectar corrupción temprana.

        Errores:
            ErrorConexion: si no se puede abrir el archivo o
                aplicar la configuración.
            ErrorIntegridad: si la verificación básica falla.
        """
        if self._conexion is not None:
            raise ErrorConexion("La base de datos ya está abierta")

        # Asegurar que la carpeta padre exista
        try:
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise ErrorConexion(
                f"No se pudo crear la carpeta {self.ruta.parent}: {e}"
            ) from e

        try:
            self._conexion = sqlite3.connect(
                self.ruta,
                # Detectar tipos y permitir conversiones
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                # Aislar transacciones para controlarlas manualmente
                isolation_level=None,  # manejamos BEGIN/COMMIT a mano
                # Deshabilitar chequeo de hilos (app single-user)
                check_same_thread=False,
            )
            # Acceso por nombre a columnas (fila["nombre"], no fila[0]).
            # sqlite3.Row se comporta como tupla Y como dict, lo que
            # hace el código mucho más legible sin costo de performance.
            self._conexion.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            raise ErrorConexion(
                f"No se pudo abrir la base en {self.ruta}: {e}"
            ) from e

        # Configuración crítica. El orden importa: primero WAL y
        # foreign_keys, después el resto.
        self._aplicar_pragmas()

        # Verificación rápida. No corre un integrity_check completo
        # (que puede tardar con bases grandes), sino un chequeo
        # básico que detecta corrupción estructural.
        self._verificacion_rapida()

    def cerrar(self) -> None:
        """
        Cierra la conexión limpiamente.

        Es importante cerrar antes de que termine el programa para
        que SQLite haga checkpoint del WAL (mover los cambios del
        archivo -wal al .db principal).
        """
        if self._conexion is None:
            return
        try:
            # Checkpoint explícito del WAL para dejar todo en el .db
            self._conexion.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            # Si falla el checkpoint, igual cerramos
            pass
        try:
            self._conexion.close()
        finally:
            self._conexion = None
            self._profundidad_transaccion = 0

    def __enter__(self) -> "BaseDatos":
        """Permite usar la clase en un bloque with."""
        self.abrir()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Cierra la conexión al salir del bloque with."""
        self.cerrar()

    # ============================================================
    # Configuración de PRAGMAs
    # ============================================================

    def _aplicar_pragmas(self) -> None:
        """
        Aplica la configuración de SQLite específica para finanzas.

        Cada PRAGMA tiene un por qué:
          - foreign_keys=ON: SQLite no enforcea FK por defecto.
            Hay que activarlo explícitamente o las FK son decorativas.
          - journal_mode=WAL: mejor concurrencia, mejor durabilidad.
          - synchronous=FULL: durabilidad ante corte de energía.
          - busy_timeout: esperar hasta 5s si otro proceso tiene lock.
          - temp_store=MEMORY: tablas temporales en RAM (más rápido).
        """
        if self._conexion is None:
            raise ErrorConexion("No hay conexión abierta")

        pragmas = [
            ("PRAGMA foreign_keys = ON", None),
            ("PRAGMA journal_mode = WAL", "journal_mode"),
            ("PRAGMA synchronous = FULL", "synchronous"),
            ("PRAGMA busy_timeout = 5000", "busy_timeout"),
            ("PRAGMA temp_store = MEMORY", "temp_store"),
        ]

        for pragma, esperado in pragmas:
            try:
                cursor = self._conexion.execute(pragma)
                resultado = cursor.fetchone()
                # Algunos PRAGMAs devuelven su valor actual. Verificamos
                # que se haya aplicado correctamente.
                if esperado and resultado:
                    valor = str(resultado[0]).lower()
                    if esperado == "journal_mode" and valor != "wal":
                        raise ErrorConexion(
                            f"No se pudo activar WAL. Modo actual: {valor}"
                        )
            except sqlite3.Error as e:
                raise ErrorConexion(
                    f"Error aplicando PRAGMA '{pragma}': {e}"
                ) from e

    # ============================================================
    # Verificación de integridad
    # ============================================================

    def _verificacion_rapida(self) -> None:
        """
        Verificación básica de la base.

        Corre PRAGMA quick_check que es mucho más rápido que
        integrity_check y detecta la mayoría de los problemas
        estructurales. Se usa al abrir.

        Si algo falla, se levanta ErrorIntegridad y NO se permite
        operar sobre la base.
        """
        if self._conexion is None:
            raise ErrorConexion("No hay conexión abierta")
        try:
            cursor = self._conexion.execute("PRAGMA quick_check")
            resultado = cursor.fetchone()
            if resultado and resultado[0] != "ok":
                raise ErrorIntegridad(
                    f"La verificación rápida falló: {resultado[0]}"
                )
        except sqlite3.Error as e:
            raise ErrorIntegridad(
                f"No se pudo verificar la integridad: {e}"
            ) from e

    def verificar_integridad_completa(self) -> bool:
        """
        Verificación profunda de toda la base.

        Es mucho más lenta que quick_check pero detecta problemas
        más sutiles. Útil antes de un backup o al cerrar el día.

        Devuelve True si todo está bien, False si hay problemas.
        No levanta excepción para permitir al caller decidir qué
        hacer (loguear, alertar, abortar).
        """
        if self._conexion is None:
            raise ErrorConexion("No hay conexión abierta")
        try:
            cursor = self._conexion.execute("PRAGMA integrity_check")
            resultados = cursor.fetchall()
            # integrity_check devuelve "ok" si todo está bien,
            # o una lista de problemas si no.
            return len(resultados) == 1 and resultados[0][0] == "ok"
        except sqlite3.Error:
            return False

    # ============================================================
    # Operaciones
    # ============================================================

    @contextmanager
    def transaccion(self) -> Iterator["BaseDatos"]:
        """
        Context manager para ejecutar un bloque de operaciones
        de forma atómica.

        REENTRANTE: si ya hay una transacción activa, esta se une
        a la existente. Solo la transacción más externa hace
        BEGIN/COMMIT/ROLLBACK. Esto permite que un servicio que
        abre una transacción llame a repositorios que a su vez
        abren su propia transacción sin conflicto.

        Uso:
            with db.transaccion():
                db.ejecutar("INSERT INTO ...")
                db.ejecutar("UPDATE ...")

        Si algo falla dentro del bloque, se hace ROLLBACK y se
        levanta ErrorTransaccion con el error original encadenado.

        Si todo va bien, se hace COMMIT al salir del bloque más
        externo.
        """
        if self._conexion is None:
            raise ErrorConexion("No hay conexión abierta")

        # Incrementar profundidad. Si es 1, somos la transacción
        # más externa y tenemos que hacer BEGIN.
        self._profundidad_transaccion += 1
        es_externa = self._profundidad_transaccion == 1

        if es_externa:
            try:
                self._conexion.execute("BEGIN")
            except sqlite3.Error as e:
                self._profundidad_transaccion -= 1
                raise ErrorTransaccion(
                    f"No se pudo iniciar la transacción: {e}"
                ) from e

        try:
            yield self
        except Exception as e:
            # Reducir profundidad
            self._profundidad_transaccion -= 1
            # Solo la transacción más externa hace rollback
            if self._profundidad_transaccion == 0:
                try:
                    self._conexion.execute("ROLLBACK")
                except sqlite3.Error:
                    pass  # si falla el rollback, el commit no se hizo igual
            # Preservar el tipo original si ya es un error nuestro
            if isinstance(e, (ErrorConexion, ErrorTransaccion)):
                raise
            raise ErrorTransaccion(f"Transacción abortada: {e}") from e

        # Camino feliz: reducir profundidad y hacer commit si
        # somos la transacción más externa
        self._profundidad_transaccion -= 1
        if self._profundidad_transaccion == 0:
            try:
                self._conexion.execute("COMMIT")
            except sqlite3.Error as e:
                # Si falla el commit, hacemos rollback por las dudas
                try:
                    self._conexion.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise ErrorTransaccion(
                    f"No se pudo confirmar la transacción: {e}"
                ) from e

    def ejecutar(self, sql: str, params: tuple | dict = ()) -> sqlite3.Cursor:
        """
        Ejecuta una sentencia SQL (INSERT, UPDATE, DELETE, etc.).

        Devuelve el cursor para permitir obtener lastrowid o
        rowcount cuando haga falta.

        Parámetros:
            sql: la sentencia.
            params: tupla o dict con los valores a bindear.
        """
        if self._conexion is None:
            raise ErrorConexion("No hay conexión abierta")
        return self._conexion.execute(sql, params)

    def consultar(self, sql: str, params: tuple | dict = ()) -> list[sqlite3.Row]:
        """
        Ejecuta un SELECT y devuelve todas las filas.

        Las filas son sqlite3.Row, que se comportan como dicts
        (fila["columna"]) y como tuplas (fila[0]). Eso es útil
        porque permite escribir código legible sin sacrificar
        performance.

        Si querés que devuelva dicts puros, podés hacer:
            [dict(r) for r in db.consultar(...)]
        """
        if self._conexion is None:
            raise ErrorConexion("No hay conexión abierta")
        cursor = self._conexion.execute(sql, params)
        return cursor.fetchall()

    def consultar_uno(
        self, sql: str, params: tuple | dict = ()
    ) -> sqlite3.Row | None:
        """Ejecuta un SELECT y devuelve la primera fila, o None."""
        if self._conexion is None:
            raise ErrorConexion("No hay conexión abierta")
        cursor = self._conexion.execute(sql, params)
        return cursor.fetchone()

    def ultimo_id_insertado(self) -> int:
        """Devuelve el último rowid insertado en esta conexión."""
        if self._conexion is None:
            raise ErrorConexion("No hay conexión abierta")
        return self._conexion.execute("SELECT last_insert_rowid()").fetchone()[0]

    # ============================================================
    # Acceso a la conexión subyacente
    # ============================================================

    @property
    def conexion(self) -> sqlite3.Connection:
        """
        Devuelve la conexión subyacente.

        Se expone para casos avanzados (ej: la API de backup de
        SQLite, que necesita el objeto de conexión). En general,
        se prefiere usar los métodos ejecutar/consultar.
        """
        if self._conexion is None:
            raise ErrorConexion("No hay conexión abierta")
        return self._conexion


def conectar(ruta: str | Path) -> BaseDatos:
    """
    Función de conveniencia para abrir una base y devolverla.

    Uso:
        db = conectar("datos/prestamos.db")
        try:
            ...
        finally:
            db.cerrar()

    O usando el with:
        with conectar("datos/prestamos.db") as db:
            ...
    """
    db = BaseDatos(ruta)
    db.abrir()
    return db