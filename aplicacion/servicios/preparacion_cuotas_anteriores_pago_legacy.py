"""Preparación de los cambios de cuotas anteriores a la cuota objetivo.

Este colaborador aplica el orden de imputación ya decidido por la política a
las obligaciones vencidas anteriores y devuelve un plan de cambios. No guarda
nada, no conoce repositorios ni abre transacciones: el manejador Legacy usa el
resultado para actualizar cuotas dentro de la transacción completa del pago.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from collections.abc import Sequence
from typing import Any

from dominio.tipos import ConceptoImputacion


@dataclass(frozen=True)
class ResultadoCuotasAnterioresPago:
    """Cambios previstos y saldos del importe todavía no aplicado."""

    actualizaciones: tuple[dict[str, Any], ...]
    restante_mora: Decimal
    restante_interes: Decimal
    restante_capital: Decimal


class PreparadorCuotasAnterioresPagoLegacy:
    """Calcula el efecto del pago sobre cuotas impagas previas a la objetivo."""

    def preparar(
        self,
        *,
        cuotas: Sequence[Any],
        cuota_objetivo: Any,
        aplicado_mora: Decimal,
        aplicado_interes: Decimal,
        aplicado_capital: Decimal,
        orden_waterfall: Sequence[ConceptoImputacion],
    ) -> ResultadoCuotasAnterioresPago:
        """Prepara cambios sin escribir ni modificar los objetos de entrada."""
        restante_mora = aplicado_mora
        restante_interes = aplicado_interes
        restante_capital = aplicado_capital
        actualizaciones: list[dict[str, Any]] = []

        for cuota in cuotas:
            if cuota.id == cuota_objetivo.id:
                break
            if cuota.total_pendiente == 0:
                continue

            saldos = {
                "MORA": cuota.mora_pendiente,
                "INTERES": cuota.interes_pendiente,
                "CAPITAL": cuota.capital_pendiente,
            }
            restantes = {
                "MORA": restante_mora,
                "INTERES": restante_interes,
                "CAPITAL": restante_capital,
            }

            # La política de pago es la única autoridad del orden de imputación.
            for concepto in orden_waterfall:
                nombre = concepto.value
                disponible = saldos[nombre]
                pendiente_pago = restantes[nombre]
                if pendiente_pago <= 0 or disponible <= 0:
                    continue
                aplicado = min(pendiente_pago, disponible)
                saldos[nombre] = disponible - aplicado
                restantes[nombre] = pendiente_pago - aplicado

            nueva_mora = saldos["MORA"]
            nuevo_interes = saldos["INTERES"]
            nuevo_capital = saldos["CAPITAL"]
            restante_mora = restantes["MORA"]
            restante_interes = restantes["INTERES"]
            restante_capital = restantes["CAPITAL"]

            if nueva_mora == 0 and nuevo_interes == 0 and nuevo_capital == 0:
                nuevo_estado = "PAGADA"
            else:
                nuevo_estado = "PARCIAL"

            sigue_pendiente = (
                nueva_mora > 0 or nuevo_interes > 0 or nuevo_capital > 0
            )
            actualizaciones.append({
                "cuota_id": cuota.id,
                "estado": nuevo_estado,
                "interes_pendiente": nuevo_interes,
                "capital_pendiente": nuevo_capital,
                "mora_pendiente": nueva_mora,
                "fue_mora": cuota.fue_mora,
                "tuvo_pago_parcial": cuota.tuvo_pago_parcial or sigue_pendiente,
                "fue_recalculada": cuota.fue_recalculada,
            })

        return ResultadoCuotasAnterioresPago(
            actualizaciones=tuple(actualizaciones),
            restante_mora=restante_mora,
            restante_interes=restante_interes,
            restante_capital=restante_capital,
        )


__all__ = [
    "PreparadorCuotasAnterioresPagoLegacy",
    "ResultadoCuotasAnterioresPago",
]
