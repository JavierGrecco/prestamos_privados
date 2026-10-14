"""Preparación de la cuota objetivo y de las imputaciones del pago Legacy.

Este colaborador calcula los cambios que se guardarán en la cuota objetivo y
construye las imputaciones que recibirá el repositorio de pagos. No consulta
repositorios, no escribe datos y no abre transacciones: la autoridad y la
persistencia siguen en el manejador de registro.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ResultadoPreparacionCuotaObjetivoPago:
    """Resultado listo para que el manejador lo aplique en su transacción."""

    actualizacion: dict[str, Any]
    imputaciones: tuple[dict[str, Any], ...]
    interes_extra_generado: Decimal


class PreparadorCuotaObjetivoPagoLegacy:
    """Prepara la cuota objetivo sin modificar la cuota ni acceder a datos externos."""

    def preparar(
        self,
        *,
        cuota_objetivo: Any,
        deuda: Mapping[str, Any],
        restante_mora: Decimal,
        restante_interes: Decimal,
        restante_capital: Decimal,
        aplicado_mora: Decimal,
        aplicado_interes: Decimal,
        aplicado_capital: Decimal,
        monto_a_capital: Decimal,
        tasa_mensual: Decimal,
        interes_compensatorio_post_vencimiento: bool,
    ) -> ResultadoPreparacionCuotaObjetivoPago:
        """Calcula saldo pendiente, evidencia de imputación e interés adicional.

        Se conservan por separado los importes remanentes que llegan desde las
        cuotas anteriores y los importes originales del simulador que se guardan
        como imputaciones. Esa separación reproduce la semántica Legacy actual.
        """
        nueva_mora = deuda["mora_nueva"] - min(
            restante_mora, deuda["mora_nueva"]
        )
        nuevo_interes = (
            deuda["cuota_interes"] + deuda["interes_extra"]
        ) - min(
            restante_interes,
            deuda["cuota_interes"] + deuda["interes_extra"],
        )
        nuevo_capital = deuda["cuota_capital"] - min(
            restante_capital, deuda["cuota_capital"]
        )

        interes_extra_generado = Decimal("0.00")
        if interes_compensatorio_post_vencimiento and nuevo_capital > 0:
            interes_extra_generado = (
                nuevo_capital * tasa_mensual
            ).quantize(Decimal("0.01"))

        if nueva_mora == 0 and nuevo_interes == 0 and nuevo_capital == 0:
            nuevo_estado = "PAGADA"
        else:
            nuevo_estado = "PARCIAL"

        sigue_pendiente = (
            nueva_mora > 0 or nuevo_interes > 0 or nuevo_capital > 0
        )
        actualizacion = {
            "cuota_id": cuota_objetivo.id,
            "estado": nuevo_estado,
            "interes_pendiente": nuevo_interes,
            "capital_pendiente": nuevo_capital,
            "mora_pendiente": nueva_mora,
            "fue_mora": (
                cuota_objetivo.fue_mora or deuda["mora_nueva"] > 0
            ),
            "tuvo_pago_parcial": (
                cuota_objetivo.tuvo_pago_parcial or sigue_pendiente
            ),
            "fue_recalculada": cuota_objetivo.fue_recalculada,
        }

        # Mantener el orden y la base de importes usados por el registro Legacy.
        imputaciones: list[dict[str, Any]] = []
        if aplicado_mora > 0:
            imputaciones.append({
                "cuota_id": cuota_objetivo.id,
                "concepto": "MORA",
                "monto": aplicado_mora,
            })
        if aplicado_interes > 0:
            imputaciones.append({
                "cuota_id": cuota_objetivo.id,
                "concepto": "INTERES",
                "monto": aplicado_interes,
            })
        capital_imputado = aplicado_capital + monto_a_capital
        if capital_imputado > 0:
            imputaciones.append({
                "cuota_id": cuota_objetivo.id,
                "concepto": "CAPITAL",
                "monto": capital_imputado,
            })

        return ResultadoPreparacionCuotaObjetivoPago(
            actualizacion=actualizacion,
            imputaciones=tuple(imputaciones),
            interes_extra_generado=interes_extra_generado,
        )


__all__ = [
    "PreparadorCuotaObjetivoPagoLegacy",
    "ResultadoPreparacionCuotaObjetivoPago",
]
