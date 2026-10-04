"""
Tests de integración de la capa de base de datos.

Validan que:
  - La conexión se abre y cierra correctamente.
  - Los PRAGMAs se aplican como esperamos.
  - Las transacciones son atómicas (rollback ante error).
  - La verificación de integridad funciona.
  - El context manager cierra la conexión al salir.
  - Se pueden ejecutar operaciones básicas.
"""
import os
from pathlib import Path

import pytest

from infraestructura import (
    BaseDatos,
    conectar,
    ErrorConexion,
    ErrorTransaccion,
)


@pytest.fixture
def ruta_temporal(tmp_path: Path) -> Path:
    """Crea una ruta temporal para cada test. Se borra al terminar."""
    return tmp_path / "test_prestamos.db"


class TestConexion:

    def test_abrir_crea_archivo(self, ruta_temporal):
        """Al abrir una base nueva, el archivo se crea."""
        db = BaseDatos(ruta_temporal)
        db.abrir()
        try:
            assert ruta_temporal.exists()
        finally:
            db.cerrar()

    def test_abrir_dos_veces_falla(self, ruta_temporal):
        """No se puede abrir una base ya abierta."""
        db = BaseDatos(ruta_temporal)
        db.abrir()
        try:
            with pytest.raises(ErrorConexion):
                db.abrir()
        finally:
            db.cerrar()

    def test_context_manager_cierra(self, ruta_temporal):
        """El bloque with cierra la conexión automáticamente."""
        with BaseDatos(ruta_temporal) as db:
            # Dentro del with, la conexión existe
            assert db._conexion is not None
        # Al salir, se cerró
        assert db._conexion is None

    def test_operar_sin_abrir_falla(self, ruta_temporal):
        """Sin abrir, las operaciones fallan."""
        db = BaseDatos(ruta_temporal)
        with pytest.raises(ErrorConexion):
            db.ejecutar("SELECT 1")

    def test_conectar_funciona(self, ruta_temporal):
        """La función conectar() abre y devuelve una base lista."""
        db = conectar(ruta_temporal)
        try:
            assert db._conexion is not None
        finally:
            db.cerrar()


class TestPragmas:

    def test_foreign_keys_activo(self, ruta_temporal):
        """Las foreign keys deben estar activas."""
        with BaseDatos(ruta_temporal) as db:
            resultado = db.consultar_uno("PRAGMA foreign_keys")
            assert resultado[0] == 1

    def test_wal_activo(self, ruta_temporal):
        """El modo journal debe ser WAL."""
        with BaseDatos(ruta_temporal) as db:
            resultado = db.consultar_uno("PRAGMA journal_mode")
            assert resultado[0].lower() == "wal"

    def test_synchronous_full(self, ruta_temporal):
        """El modo synchronous debe ser FULL (2)."""
        with BaseDatos(ruta_temporal) as db:
            resultado = db.consultar_uno("PRAGMA synchronous")
            # 2 = FULL
            assert resultado[0] == 2

    def test_busy_timeout(self, ruta_temporal):
        """El timeout debe estar configurado."""
        with BaseDatos(ruta_temporal) as db:
            resultado = db.consultar_uno("PRAGMA busy_timeout")
            assert resultado[0] == 5000


class TestOperacionesBasicas:

    def test_crear_tabla_e_insertar(self, ruta_temporal):
        """Se puede crear una tabla e insertar datos."""
        with BaseDatos(ruta_temporal) as db:
            db.ejecutar("""
                CREATE TABLE prueba (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    monto REAL
                )
            """)
            db.ejecutar(
                "INSERT INTO prueba (nombre, monto) VALUES (?, ?)",
                ("test", 1234.56),
            )
            fila = db.consultar_uno("SELECT * FROM prueba WHERE nombre = ?", ("test",))
            assert fila is not None
            assert fila["nombre"] == "test"
            assert fila["monto"] == 1234.56

    def test_row_factory_permite_acceso_por_nombre(self, ruta_temporal):
        """Las filas se acceden por nombre, no solo por índice."""
        with BaseDatos(ruta_temporal) as db:
            db.ejecutar("CREATE TABLE t (a INTEGER, b TEXT)")
            db.ejecutar("INSERT INTO t VALUES (1, 'hola')")
            fila = db.consultar_uno("SELECT * FROM t")
            assert fila["a"] == 1
            assert fila["b"] == "hola"
            assert fila[0] == 1
            assert fila[1] == "hola"

    def test_ultimo_id_insertado(self, ruta_temporal):
        """Devuelve el ID del último insert."""
        with BaseDatos(ruta_temporal) as db:
            db.ejecutar("CREATE TABLE t (id INTEGER PRIMARY KEY, x TEXT)")
            db.ejecutar("INSERT INTO t (x) VALUES ('a')")
            id1 = db.ultimo_id_insertado()
            db.ejecutar("INSERT INTO t (x) VALUES ('b')")
            id2 = db.ultimo_id_insertado()
            assert id2 == id1 + 1


class TestTransacciones:

    def test_commit_exitoso(self, ruta_temporal):
        """Una transacción exitosa persiste los cambios."""
        with BaseDatos(ruta_temporal) as db:
            db.ejecutar("CREATE TABLE t (id INTEGER PRIMARY KEY, x TEXT)")
            with db.transaccion():
                db.ejecutar("INSERT INTO t (x) VALUES ('a')")
                db.ejecutar("INSERT INTO t (x) VALUES ('b')")
            filas = db.consultar("SELECT * FROM t ORDER BY id")
            assert len(filas) == 2

    def test_rollback_ante_error(self, ruta_temporal):
        """Una transacción con error hace rollback completo."""
        with BaseDatos(ruta_temporal) as db:
            db.ejecutar("CREATE TABLE t (id INTEGER PRIMARY KEY, x TEXT NOT NULL)")
            with pytest.raises(ErrorTransaccion):
                with db.transaccion():
                    db.ejecutar("INSERT INTO t (x) VALUES ('a')")
                    # Este insert falla porque x no puede ser NULL
                    db.ejecutar("INSERT INTO t (x) VALUES (NULL)")
            # El primer insert también se revirtió
            filas = db.consultar("SELECT * FROM t")
            assert len(filas) == 0

    def test_rollback_preserva_error_original(self, ruta_temporal):
        """El error original se preserva como causa."""
        with BaseDatos(ruta_temporal) as db:
            db.ejecutar("CREATE TABLE t (id INTEGER PRIMARY KEY, x TEXT)")
            with pytest.raises(ErrorTransaccion) as exc_info:
                with db.transaccion():
                    db.ejecutar("INSERT INTO t (x) VALUES ('a')")
                    raise ValueError("error de prueba")
            # El error original está encadenado
            assert "error de prueba" in str(exc_info.value)


class TestIntegridad:

    def test_verificacion_rapida_pasa_en_base_nueva(self, ruta_temporal):
        """Una base nueva pasa la verificación rápida."""
        with BaseDatos(ruta_temporal) as db:
            # Si llegó hasta acá, la verificación rápida ya pasó
            # (se corre al abrir). Ahora verificamos que el método
            # completo también funcione.
            assert db.verificar_integridad_completa() is True

    def test_verificacion_completa_en_base_con_datos(self, ruta_temporal):
        """La verificación completa funciona con datos cargados."""
        with BaseDatos(ruta_temporal) as db:
            db.ejecutar("CREATE TABLE t (id INTEGER PRIMARY KEY, x TEXT)")
            with db.transaccion():
                for i in range(100):
                    db.ejecutar("INSERT INTO t (x) VALUES (?)", (f"fila_{i}",))
            assert db.verificar_integridad_completa() is True


class TestDatosPersistentes:

    def test_datos_sobreviven_cierre(self, ruta_temporal):
        """Los datos se persisten al cerrar y reabrir."""
        # Primera sesión: escribimos
        with BaseDatos(ruta_temporal) as db:
            db.ejecutar("CREATE TABLE t (id INTEGER PRIMARY KEY, x TEXT)")
            with db.transaccion():
                db.ejecutar("INSERT INTO t (x) VALUES ('persistente')")

        # Segunda sesión: leemos
        with BaseDatos(ruta_temporal) as db:
            fila = db.consultar_uno("SELECT x FROM t")
            assert fila is not None
            assert fila["x"] == "persistente"