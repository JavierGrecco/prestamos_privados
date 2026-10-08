"""Políticas puras de devengamiento incremental V3-G1."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping

from .devengamiento_v3 import PoliticaInteres, calcular_devengamiento_interes
from .excepciones import ErrorValidacion
from .motor_pagos_v3 import Devengamiento, ObligacionSnapshot
from .politica_pago import BaseMoraPago
from .tipos import ConceptoImputacion, ConvencionDias, ModalidadTasa, ZERO

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


ORIGEN_MORA_CONTRACTUAL = "MORA_CONTRACTUAL"


@dataclass(frozen=True)
class PoliticaMoraContractualV3:
    """Política de mora contractual usada hoy por la ruta Legacy.

    La tasa vigente del proyecto es 50% anual con convención ACTUAL/365.
    La base es la cuota contractual completa y solo se genera mora nueva para
    la primera obligación PENDIENTE que ya venció.
    """

    tasa_anual: Decimal = Decimal("0.50")
    convencion_dias: ConvencionDias = ConvencionDias.ACTUAL_365
    base: BaseMoraPago = BaseMoraPago.CUOTA_CONTRACTUAL

    def __post_init__(self) -> None:
        politica = PoliticaInteres(
            tasa_anual=self.tasa_anual,
            modalidad_tasa=ModalidadTasa.TNA,
            convencion_dias=self.convencion_dias,
            concepto=ConceptoImputacion.MORA,
            origen=ORIGEN_MORA_CONTRACTUAL,
        )
        object.__setattr__(self, "tasa_anual", politica.tasa_anual)
        if self.convencion_dias is not ConvencionDias.ACTUAL_365:
            raise ErrorValidacion(
                "La mora contractual V3 requiere convención ACTUAL_365"
            )

    @property
    def origen(self) -> str:
        return ORIGEN_MORA_CONTRACTUAL


def generar_mora_contractual(
    *,
    obligaciones: tuple[ObligacionSnapshot, ...],
    fecha_valor: date,
    politica: PoliticaMoraContractualV3,
    ultimo_hasta_por_cuota: Mapping[int, date | None] | None = None,
) -> dict[int, tuple[Devengamiento, ...]]:
    """Genera la mora nueva de la primera obligación pendiente y vencida."""

    ultimo_hasta_por_cuota = ultimo_hasta_por_cuota or {}

    objetivo = next(
        (
            obligacion
            for obligacion in obligaciones
            if obligacion.estado == "PENDIENTE"
            and obligacion.saldo.total > ZERO
        ),
        None,
    )
    if objetivo is None:
        return {}
    if fecha_valor <= objetivo.vencimiento:
        return {}
    base_mora = (
        objetivo.monto_mora_base
        if politica.base is BaseMoraPago.CUOTA_CONTRACTUAL
        else objetivo.saldo.capital
    )
    if base_mora <= ZERO:
        return {}

    ultimo_hasta = ultimo_hasta_por_cuota.get(objetivo.cuota_id)
    if objetivo.saldo.mora > ZERO and ultimo_hasta is None:
        return {}

    fecha_desde = max(objetivo.vencimiento, ultimo_hasta or objetivo.vencimiento)
    if fecha_valor <= fecha_desde:
        return {}

    politica_base = PoliticaInteres(
        tasa_anual=politica.tasa_anual,
        modalidad_tasa=ModalidadTasa.TNA,
        convencion_dias=politica.convencion_dias,
        concepto=ConceptoImputacion.MORA,
        origen=politica.origen,
    )
    dev = calcular_devengamiento_interes(
        base=base_mora,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_valor,
        politica=politica_base,
        referencia=(
            f"cuota:{objetivo.cuota_id}:mora:"
            f"{fecha_desde.isoformat()}:{fecha_valor.isoformat()}"
        ),
    )
    if dev.monto <= ZERO:
        return {}
    return {objetivo.cuota_id: (dev,)}

