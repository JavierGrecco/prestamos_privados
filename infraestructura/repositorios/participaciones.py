"""
Repositorio de participaciones de inversores.

Una participación representa cuánto aporta cada inversor a un
préstamo, y qué porcentaje del total le corresponde.
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
)
from .modelos import Participacion


class ParticipacionRepo(RepositorioBase):
    """Acceso a la tabla `participaciones`."""

    def __init__(self, db: BaseDatos):
        super().__init__(db)

    def crear(
        self,
        prestamo_id: int,
        inversor_id: int,
        capital_aportado: Decimal,
        porcentaje: Decimal,
        fecha_aporte: date,
        tc_aporte: Decimal | None = None,
        capital_usd_ref: Decimal | None = None,
    ) -> int:
        """
        Crea una participación.

        Devuelve el ID de la participación creada.

        Errores:
            ValueError: si el capital es <= 0 o el porcentaje no está
                entre 0 y 1.
        """
        if capital_aportado <= 0:
            raise ValueError("El capital aportado debe ser mayor a cero")
        if not (Decimal("0") < porcentaje <= Decimal("1")):
            raise ValueError("El porcentaje debe estar entre 0 y 1")

        with self.db.transaccion():
            self.db.ejecutar(
                """
                INSERT INTO participaciones
                (prestamo_id, inversor_id, capital_aportado, moneda_aporte,
                 tc_aporte, capital_usd_ref, porcentaje, fecha_aporte,
                 estado, creado_en)
                VALUES (?, ?, ?, 'ARS', ?, ?, ?, ?, 'ACTIVA', ?)
                """,
                (
                    prestamo_id,
                    inversor_id,
                    decimal_a_str(capital_aportado),
                    decimal_a_str(tc_aporte),
                    decimal_a_str(capital_usd_ref),
                    decimal_a_str(porcentaje),
                    fecha_a_iso(fecha_aporte),
                    ahora_iso(),
                ),
            )
            return self.db.ultimo_id_insertado()

    def obtener(self, participacion_id: int) -> Participacion | None:
        """Devuelve una participación por ID."""
        fila = self.db.consultar_uno(
            "SELECT * FROM participaciones WHERE id = ?",
            (participacion_id,),
        )
        return self._fila_a_participacion(fila) if fila else None

    def por_prestamo(self, prestamo_id: int) -> list[Participacion]:
        """Lista las participaciones activas de un préstamo."""
        filas = self.db.consultar(
            """
            SELECT * FROM participaciones
            WHERE prestamo_id = ? AND estado = 'ACTIVA'
            ORDER BY fecha_aporte, id
            """,
            (prestamo_id,),
        )
        return [self._fila_a_participacion(f) for f in filas]

    def por_inversor(self, inversor_id: int) -> list[Participacion]:
        """Lista las participaciones de un inversor."""
        filas = self.db.consultar(
            """
            SELECT * FROM participaciones
            WHERE inversor_id = ?
            ORDER BY fecha_aporte DESC
            """,
            (inversor_id,),
        )
        return [self._fila_a_participacion(f) for f in filas]

    def suma_porcentajes(self, prestamo_id: int) -> Decimal:
        """
        Suma los porcentajes activos de un préstamo.

        Debe dar exactamente 1.0 cuando el préstamo está completo.
        Si da menos, falta asignar capital. Si da más, hay error.
        """
        filas = self.db.consultar(
            """
            SELECT porcentaje FROM participaciones
            WHERE prestamo_id = ? AND estado = 'ACTIVA'
            """,
            (prestamo_id,),
        )
        total = sum((str_a_decimal(f["porcentaje"]) for f in filas), Decimal("0"))
        return total

    # ============================================================
    # Conversión
    # ============================================================

    def _fila_a_participacion(self, fila) -> Participacion:
        return Participacion(
            id=fila["id"],
            prestamo_id=fila["prestamo_id"],
            inversor_id=fila["inversor_id"],
            capital_aportado=str_a_decimal(fila["capital_aportado"]),
            moneda_aporte=fila["moneda_aporte"],
            tc_aporte=str_a_decimal(fila["tc_aporte"]) if fila["tc_aporte"] else None,
            capital_usd_ref=str_a_decimal(fila["capital_usd_ref"]) if fila["capital_usd_ref"] else None,
            porcentaje=str_a_decimal(fila["porcentaje"]),
            fecha_aporte=iso_a_fecha(fila["fecha_aporte"]),
            estado=fila["estado"],
            creado_en=fila["creado_en"],
        )