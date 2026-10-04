"""
Repositorio del historial de recálculos.
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
from .modelos import HistorialRecalculo


class RecalculoRepo(RepositorioBase):
    """Acceso a la tabla `historial_recalculos`."""

    def __init__(self, db: BaseDatos):
        super().__init__(db)

    def registrar(
        self,
        prestamo_id: int,
        pago_id: int,
        tipo: str,
        fecha: date,
        capital_antes: Decimal,
        capital_despues: Decimal,
        cuotas_antes: int,
        cuotas_despues: int,
        intereses_antes: Decimal,
        intereses_despues: Decimal,
        detalle_json: str | None = None,
        cuota_objetivo_numero: int = 0,
    ) -> int:
        if tipo not in ("RAI", "RNI"):
            raise ValueError(f"Tipo inválido: {tipo}. Debe ser RAI o RNI.")

        with self.db.transaccion():
            self.db.ejecutar(
                """
                INSERT INTO historial_recalculos
                (prestamo_id, pago_id, tipo, fecha,
                 capital_antes, capital_despues,
                 cuotas_antes, cuotas_despues,
                 intereses_antes, intereses_despues,
                 detalle_json, creado_en,
                 cuota_objetivo_numero)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prestamo_id,
                    pago_id,
                    tipo,
                    fecha_a_iso(fecha),
                    decimal_a_str(capital_antes),
                    decimal_a_str(capital_despues),
                    cuotas_antes,
                    cuotas_despues,
                    decimal_a_str(intereses_antes),
                    decimal_a_str(intereses_despues),
                    detalle_json,
                    ahora_iso(),
                    cuota_objetivo_numero,
                ),
            )
            return self.db.ultimo_id_insertado()

    def por_prestamo(self, prestamo_id: int) -> list[HistorialRecalculo]:
        filas = self.db.consultar(
            """
            SELECT * FROM historial_recalculos
            WHERE prestamo_id = ?
            ORDER BY fecha, id
            """,
            (prestamo_id,),
        )
        return [self._fila_a_recalculo(f) for f in filas]

    def _fila_a_recalculo(self, fila) -> HistorialRecalculo:
        def _leer(nombre, default=0):
            try:
                return fila[nombre]
            except (KeyError, IndexError):
                return default

        return HistorialRecalculo(
            id=fila["id"],
            prestamo_id=fila["prestamo_id"],
            pago_id=fila["pago_id"],
            tipo=fila["tipo"],
            fecha=iso_a_fecha(fila["fecha"]),
            capital_antes=str_a_decimal(fila["capital_antes"]),
            capital_despues=str_a_decimal(fila["capital_despues"]),
            cuotas_antes=fila["cuotas_antes"],
            cuotas_despues=fila["cuotas_despues"],
            intereses_antes=str_a_decimal(fila["intereses_antes"]),
            intereses_despues=str_a_decimal(fila["intereses_despues"]),
            detalle_json=fila["detalle_json"],
            creado_en=fila["creado_en"],
            cuota_objetivo_numero=_leer("cuota_objetivo_numero", 0) or 0,
        )