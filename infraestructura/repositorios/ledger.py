"""
Repositorio del ledger (libro mayor).

El ledger es el registro de doble entrada de todas las operaciones
financieras. Es inmutable: sus movimientos nunca se actualizan ni
se borran. Si hay que revertir algo, se crea un movimiento
compensatorio con signo opuesto.

## ¿Qué es doble entrada?
Cada operación financiera afecta al menos dos cuentas. Por ejemplo,
cuando se desembolsa un préstamo:
  - El préstamo (activo) aumenta: DEBE al préstamo.
  - El inversor (pasivo) aumenta: HABER al inversor.

La suma de todos los DEBE debe ser siempre igual a la suma de todos
los HABER. Si no lo es, hay un bug.

## ¿Por qué es importante?
Sin ledger, un saldo es un número que se sobrescribe. Con ledger, el
saldo se RECONSTRUYE sumando los movimientos. Eso permite saber el
estado a cualquier fecha pasada, auditar sin ambigüedad, y detectar
inconsistencias automáticamente.
"""
from datetime import date
from decimal import Decimal
from ..db import BaseDatos
from .base import (
    RepositorioBase,
    ahora_iso,
    fecha_a_iso,
    iso_a_fecha,
    decimal_a_str,
    str_a_decimal,
    nuevo_correlacion_id,
)
from .modelos import MovimientoLedger


class LedgerRepo(RepositorioBase):
    """Acceso a la tabla `ledger`."""

    def __init__(self, db: BaseDatos):
        super().__init__(db)

    # ============================================================
    # Registro de movimientos
    # ============================================================

    def registrar_movimiento(
        self,
        entidad: str,
        entidad_id: int,
        tipo_movimiento: str,
        debe: Decimal,
        haber: Decimal,
        fecha: date,
        correlacion_id: str,
        metadata: str | None = None,
    ) -> int:
        """
        Registra un movimiento en el ledger.
        El ledger es inmutable: una vez insertado, el movimiento
        no se puede modificar. Si hay que revertir, se registra
        otro movimiento con signos opuestos.

        Parámetros:
            entidad: PRESTAMO, INVERSOR, PAGO o CUOTA.
            entidad_id: ID de la entidad afectada.
            tipo_movimiento: descripción del tipo (APORTE, PAGO,
                INTERES_DEVENGADO, etc.).
            debe: monto en el debe.
            haber: monto en el haber.
            fecha: fecha económica del movimiento.
            correlacion_id: ID que vincula todos los movimientos
                de una misma operación.
            metadata: JSON opcional con contexto adicional.

        Devuelve el ID del movimiento creado.
        """
        if debe < 0 or haber < 0:
            raise ValueError("Ni el debe ni el haber pueden ser negativos")
        if debe == 0 and haber == 0:
            raise ValueError("Un movimiento no puede tener debe y haber en cero")
        with self.db.transaccion():
            self.db.ejecutar(
                """
                INSERT INTO ledger
                (entidad, entidad_id, tipo_movimiento, debe, haber,
                 fecha, metadata, correlacion_id, creado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entidad,
                    entidad_id,
                    tipo_movimiento,
                    decimal_a_str(debe),
                    decimal_a_str(haber),
                    fecha_a_iso(fecha),
                    metadata,
                    correlacion_id,
                    ahora_iso(),
                ),
            )
            return self.db.ultimo_id_insertado()

    def registrar_operacion(
        self,
        movimientos: list[dict],
        correlacion_id: str | None = None,
    ) -> tuple[list[int], str]:
        """
        Registra una operación completa con múltiples movimientos.

        Verifica la invariante de doble entrada: la suma de debe
        debe ser igual a la suma de haber. Si no, rechaza toda la
        operación.

        Cada movimiento es un dict con:
            {entidad, entidad_id, tipo_movimiento, debe, haber,
             fecha, metadata (opcional)}

        Devuelve:
            (lista de IDs creados, correlacion_id usado).
        """
        if not movimientos:
            raise ValueError("Una operación debe tener al menos un movimiento")

        # Verificar doble entrada usando Decimal exacto.
        suma_debe = sum(
            (Decimal(str(m["debe"])) for m in movimientos), Decimal("0")
        )
        suma_haber = sum(
            (Decimal(str(m["haber"])) for m in movimientos), Decimal("0")
        )
        if suma_debe != suma_haber:
            raise ValueError(
                f"El asiento no cuadra: debe={suma_debe}, haber={suma_haber}"
            )

        correlacion_id = correlacion_id or nuevo_correlacion_id()
        ids = []
        with self.db.transaccion():
            for mov in movimientos:
                self.db.ejecutar(
                    """
                    INSERT INTO ledger
                    (entidad, entidad_id, tipo_movimiento, debe, haber,
                     fecha, metadata, correlacion_id, creado_en)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mov["entidad"],
                        mov["entidad_id"],
                        mov["tipo_movimiento"],
                        decimal_a_str(Decimal(str(mov["debe"]))),
                        decimal_a_str(Decimal(str(mov["haber"]))),
                        fecha_a_iso(mov["fecha"]),
                        mov.get("metadata"),
                        correlacion_id,
                        ahora_iso(),
                    ),
                )
                ids.append(self.db.ultimo_id_insertado())
        return ids, correlacion_id

    # ============================================================
    # Consultas
    # ============================================================

    def por_entidad(
        self,
        entidad: str,
        entidad_id: int,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[MovimientoLedger]:
        """Devuelve los movimientos de una entidad."""
        condiciones = ["entidad = ?", "entidad_id = ?"]
        params = [entidad, entidad_id]
        if desde:
            condiciones.append("fecha >= ?")
            params.append(fecha_a_iso(desde))
        if hasta:
            condiciones.append("fecha <= ?")
            params.append(fecha_a_iso(hasta))
        where = " AND ".join(condiciones)
        filas = self.db.consultar(
            f"SELECT * FROM ledger WHERE {where} ORDER BY fecha, id",
            tuple(params),
        )
        return [self._fila_a_movimiento(f) for f in filas]

    def por_correlacion(self, correlacion_id: str) -> list[MovimientoLedger]:
        """Devuelve todos los movimientos de una misma operación."""
        filas = self.db.consultar(
            "SELECT * FROM ledger WHERE correlacion_id = ? ORDER BY id",
            (correlacion_id,),
        )
        return [self._fila_a_movimiento(f) for f in filas]

    def saldo(
        self,
        entidad: str,
        entidad_id: int,
        hasta: date | None = None,
    ) -> Decimal:
        """
        Calcula el saldo de una entidad hasta una fecha.
        Es la suma de todos los debe menos la suma de todos los
        haber. Si no se pasa fecha, se calcula hasta hoy.

        Los importes se almacenan como TEXT y se suman como Decimal
        en Python. No se usa SQLite SUM(... AS REAL), para evitar
        perdida de precision binaria en importes monetarios.
        """
        condiciones = ["entidad = ?", "entidad_id = ?"]
        params = [entidad, entidad_id]
        if hasta:
            condiciones.append("fecha <= ?")
            params.append(fecha_a_iso(hasta))
        where = " AND ".join(condiciones)
        filas = self.db.consultar(
            f"SELECT debe, haber FROM ledger WHERE {where} ORDER BY fecha, id",
            tuple(params),
        )
        suma_debe = sum(
            (str_a_decimal(fila["debe"]) for fila in filas), Decimal("0")
        )
        suma_haber = sum(
            (str_a_decimal(fila["haber"]) for fila in filas), Decimal("0")
        )
        return suma_debe - suma_haber

    def verificar_cuadre(self) -> bool:
        """
        Verifica que el ledger cuadre globalmente.
        Suma todos los debe y todos los haber. Si son iguales,
        devuelve True. Si no, hay un bug grave.

        La comparación se hace usando Decimal exacto porque los
        importes del ledger son valores monetarios almacenados como TEXT.
        """
        filas = self.db.consultar("SELECT debe, haber FROM ledger")
        suma_debe = sum(
            (str_a_decimal(fila["debe"]) for fila in filas), Decimal("0")
        )
        suma_haber = sum(
            (str_a_decimal(fila["haber"]) for fila in filas), Decimal("0")
        )
        return suma_debe == suma_haber

    # ============================================================
    # Conversión
    # ============================================================

    def _fila_a_movimiento(self, fila) -> MovimientoLedger:
        return MovimientoLedger(
            id=fila["id"],
            entidad=fila["entidad"],
            entidad_id=fila["entidad_id"],
            tipo_movimiento=fila["tipo_movimiento"],
            debe=str_a_decimal(fila["debe"]),
            haber=str_a_decimal(fila["haber"]),
            fecha=iso_a_fecha(fila["fecha"]),
            metadata=fila["metadata"],
            correlacion_id=fila["correlacion_id"],
            creado_en=fila["creado_en"],
        )
