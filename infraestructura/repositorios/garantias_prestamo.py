"""Repositorio de garantías personales ligadas a préstamos.

La garantía se registra como una relación auditable; no es un movimiento del
ledger ni modifica saldos o reglas de pago.
"""
from datetime import date
from decimal import Decimal

from ..db import BaseDatos
from .base import (
    RepositorioBase,
    ahora_iso,
    decimal_a_str,
    fecha_a_iso,
    iso_a_fecha,
    str_a_decimal,
)
from .modelos import GarantiaPrestamo


class GarantiaPrestamoRepo(RepositorioBase):
    """Acceso a garantías personales y su historial."""

    def __init__(self, db: BaseDatos):
        super().__init__(db)

    def crear(
        self,
        *,
        prestamo_id: int,
        garante_id: int,
        alcance: str,
        monto_maximo: Decimal | None,
        fecha_constitucion: date,
        creado_por: str,
        ahora: str | None = None,
    ) -> int:
        """Registra una garantía activa sin sobreescribir relaciones previas."""
        ahora = ahora or ahora_iso()
        with self.db.transaccion():
            self.db.ejecutar(
                """
                INSERT INTO garantias_prestamo
                    (prestamo_id, garante_id, alcance, monto_maximo, moneda,
                     estado, fecha_constitucion, fecha_fin, motivo_fin,
                     creado_por, creado_en, actualizado_en)
                VALUES (?, ?, ?, ?, 'ARS', 'ACTIVA', ?, NULL, NULL, ?, ?, ?)
                """,
                (
                    prestamo_id,
                    garante_id,
                    alcance,
                    decimal_a_str(monto_maximo),
                    fecha_a_iso(fecha_constitucion),
                    creado_por,
                    ahora,
                    ahora,
                ),
            )
            return self.db.ultimo_id_insertado()

    def obtener(self, garantia_id: int) -> GarantiaPrestamo | None:
        fila = self.db.consultar_uno(
            "SELECT * FROM garantias_prestamo WHERE id = ?",
            (garantia_id,),
        )
        return self._modelo(fila) if fila else None

    def por_prestamo(self, prestamo_id: int) -> tuple[GarantiaPrestamo, ...]:
        filas = self.db.consultar(
            """
            SELECT * FROM garantias_prestamo
            WHERE prestamo_id = ?
            ORDER BY id DESC
            """,
            (prestamo_id,),
        )
        return tuple(self._modelo(fila) for fila in filas)

    def por_garante(
        self,
        garante_id: int,
    ) -> tuple[GarantiaPrestamo, ...]:
        filas = self.db.consultar(
            """
            SELECT * FROM garantias_prestamo
            WHERE garante_id = ?
            ORDER BY fecha_constitucion DESC, id DESC
            """,
            (garante_id,),
        )
        return tuple(self._modelo(fila) for fila in filas)

    def activa_para_par(
        self,
        prestamo_id: int,
        garante_id: int,
    ) -> GarantiaPrestamo | None:
        fila = self.db.consultar_uno(
            """
            SELECT * FROM garantias_prestamo
            WHERE prestamo_id = ? AND garante_id = ? AND estado = 'ACTIVA'
            """,
            (prestamo_id, garante_id),
        )
        return self._modelo(fila) if fila else None

    def finalizar(
        self,
        *,
        garantia_id: int,
        estado: str,
        fecha_fin: date,
        motivo: str,
        ahora: str | None = None,
    ) -> None:
        """Finaliza una relación activa conservando su historial."""
        if estado not in {"LIBERADA", "ANULADA"}:
            raise ValueError("El estado final de una garantía no es válido.")
        ahora = ahora or ahora_iso()
        self.db.ejecutar(
            """
            UPDATE garantias_prestamo
            SET estado = ?, fecha_fin = ?, motivo_fin = ?, actualizado_en = ?
            WHERE id = ? AND estado = 'ACTIVA'
            """,
            (estado, fecha_a_iso(fecha_fin), motivo, ahora, garantia_id),
        )

    @staticmethod
    def _modelo(fila) -> GarantiaPrestamo:
        return GarantiaPrestamo(
            id=int(fila["id"]),
            prestamo_id=int(fila["prestamo_id"]),
            garante_id=int(fila["garante_id"]),
            alcance=str(fila["alcance"]),
            monto_maximo=(
                str_a_decimal(fila["monto_maximo"])
                if fila["monto_maximo"] is not None
                else None
            ),
            moneda=str(fila["moneda"]),
            estado=str(fila["estado"]),
            fecha_constitucion=iso_a_fecha(fila["fecha_constitucion"]),
            fecha_fin=iso_a_fecha(fila["fecha_fin"]),
            motivo_fin=fila["motivo_fin"],
            creado_por=str(fila["creado_por"]),
            creado_en=str(fila["creado_en"]),
            actualizado_en=str(fila["actualizado_en"]),
        )
