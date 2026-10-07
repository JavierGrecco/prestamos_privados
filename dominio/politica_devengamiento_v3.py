"""Políticas puras de devengamiento incremental V3-G1."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping

from .devengamiento_v3 import PoliticaInteres, calcular_devengamiento_interes
from .excepciones import ErrorValidacion
from .motor_pagos_v3 import Devengamiento, ObligacionSnapshot
from .tipos import ConceptoImputacion, ZERO

ORIGEN_INTERES_CAPITAL_PENDIENTE = "INTERES_CAPITAL_PENDIENTE"


@dataclass(frozen=True)
class PoliticaInteresCapitalPendiente:
    """Política explícita para un interés incremental sobre capital pendiente."""

    politica: PoliticaInteres

    def __post_init__(self) -> None:
        if self.politica.concepto is not ConceptoImputacion.INTERES:
            raise ErrorValidacion(
                "El interés sobre capital pendiente debe imputarse como INTERES"
            )

    @property
    def origen(self) -> str:
        return ORIGEN_INTERES_CAPITAL_PENDIENTE


def generar_interes_capital_pendiente(
    *,
    obligaciones: tuple[ObligacionSnapshot, ...],
    fecha_valor: date,
    politica: PoliticaInteresCapitalPendiente,
    ultimo_hasta_por_cuota: Mapping[int, date | None] | None = None,
) -> dict[int, tuple[Devengamiento, ...]]:
    """Genera únicamente interés incremental desde el último corte conocido.

    La función no toca DB ni decide mora. La base es el capital pendiente
    vigente del snapshot; el período comienza en el último corte persistido o,
    si no existe, en el vencimiento de la obligación. Nunca se capitaliza de
    forma silenciosa.
    """
    ultimo_hasta_por_cuota = ultimo_hasta_por_cuota or {}
    resultado: dict[int, tuple[Devengamiento, ...]] = {}

    for obligacion in obligaciones:
        base = obligacion.saldo.capital
        if base <= ZERO:
            continue
        if fecha_valor <= obligacion.vencimiento:
            continue

        ultimo_hasta = ultimo_hasta_por_cuota.get(obligacion.cuota_id)
        fecha_desde = max(obligacion.vencimiento, ultimo_hasta or obligacion.vencimiento)
        if fecha_valor <= fecha_desde:
            continue

        politica_base = PoliticaInteres(
            tasa_anual=politica.politica.tasa_anual,
            modalidad_tasa=politica.politica.modalidad_tasa,
            convencion_dias=politica.politica.convencion_dias,
            concepto=ConceptoImputacion.INTERES,
            origen=politica.origen,
        )
        dev = calcular_devengamiento_interes(
            base=base,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_valor,
            politica=politica_base,
            referencia=f"cuota:{obligacion.cuota_id}:capital_pendiente:{fecha_desde.isoformat()}:{fecha_valor.isoformat()}",
        )
        if dev.monto > ZERO:
            resultado[obligacion.cuota_id] = (dev,)

    return resultado
