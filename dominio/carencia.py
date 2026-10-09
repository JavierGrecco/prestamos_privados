"""Devengamiento simple de intereses durante un período de carencia.

Este módulo calcula interés sobre capital constante entre dos fechas. No
capitaliza intereses, no persiste obligaciones y no elige si el interés debe
pagarse o diferirse: esa decisión corresponde a las condiciones del préstamo.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from .excepciones import ErrorValidacion
from .interes import interes_periodo
from .amortizacion import fraccion_anual_por_fechas, tasa_periodo_por_fechas
from .tipos import ConvencionDias, ModalidadTasa, money


@dataclass(frozen=True, slots=True)
class TramoInteresCarencia:
    """Un tramo de devengamiento calculado sobre el capital original."""

    fecha_inicio: date
    fecha_fin: date
    capital_base: Decimal
    interes: Decimal


@dataclass(frozen=True, slots=True)
class ResultadoInteresCarencia:
    """Resultado auditable del devengamiento simple en la carencia."""

    capital_base: Decimal
    fecha_inicio: date
    fecha_fin: date
    tasa_anual: Decimal
    modalidad: ModalidadTasa
    convencion: ConvencionDias
    tramos: tuple[TramoInteresCarencia, ...]
    interes_total: Decimal


def _calcular_tramo(
    *,
    capital: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    convencion: ConvencionDias,
    fecha_inicio: date,
    fecha_fin: date,
) -> tuple[TramoInteresCarencia, ...]:
    """Calcula un período de carencia con la misma autoridad temporal de amortización."""
    if fecha_fin <= fecha_inicio:
        return ()

    if convencion == ConvencionDias.MENSUAL:
        # Preserva la semántica mensual ya existente: una TEM por período.
        interes = interes_periodo(
            saldo=capital,
            tasa_anual=tasa_anual,
            modalidad=modalidad,
            convencion=convencion,
            fecha_ini=fecha_inicio,
            fecha_fin=fecha_fin,
        )
    else:
        # TNA es proporcional a la fracción de año y TEA usa su factor efectivo
        # compuesto. El capital permanece constante: el interés devengado queda
        # separado y no genera interés sobre sí mismo.
        fraccion = fraccion_anual_por_fechas(
            fecha_inicio,
            fecha_fin,
            convencion,
        )
        factor_periodo = tasa_periodo_por_fechas(
            tasa_anual=tasa_anual,
            modalidad=modalidad,
            fraccion_anual=fraccion,
        )
        interes = money(capital * factor_periodo)

    return (
        TramoInteresCarencia(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            capital_base=capital,
            interes=interes,
        ),
    )


def calcular_interes_carencia_simple(
    *,
    capital: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    convencion: ConvencionDias,
    fecha_inicio: date,
    fecha_fin: date,
) -> ResultadoInteresCarencia:
    """Calcula el interés devengado sin pagos ni capitalización de intereses.

    Los períodos se segmentan por meses anclados a la fecha inicial. Para
    MENSUAL se preserva la TEM existente; para convenciones de días se usa la
    misma fracción temporal y el mismo factor TNA/TEA que la amortización por
    fechas. El capital permanece constante y los tramos no generan interés
    sobre el interés devengado.
    """
    if capital <= 0:
        raise ErrorValidacion("El capital de carencia debe ser mayor a cero")
    if tasa_anual < 0:
        raise ErrorValidacion("La tasa anual no puede ser negativa")
    if fecha_fin < fecha_inicio:
        raise ErrorValidacion("La fecha final de carencia no puede preceder a la inicial")

    tramos: list[TramoInteresCarencia] = []
    cursor = fecha_inicio
    numero_periodo = 1
    while cursor < fecha_fin:
        fin_periodo = fecha_inicio + relativedelta(months=numero_periodo)
        if fin_periodo <= cursor:
            raise ErrorValidacion("No se pudo avanzar al siguiente período de carencia")
        fin_tramo = min(fecha_fin, fin_periodo)
        if fin_tramo < fin_periodo and convencion in {
            ConvencionDias.MENSUAL,
            ConvencionDias.TREINTA_360,
        }:
            raise ErrorValidacion(
                "Con convención MENSUAL o 30E/360, la carencia debe terminar "
                "en un aniversario mensual. Para un período irregular, usá "
                "ACTUAL_365, ACTUAL_360 o ACTUAL_ACTUAL."
            )
        tramos.extend(
            _calcular_tramo(
                capital=capital,
                tasa_anual=tasa_anual,
                modalidad=modalidad,
                convencion=convencion,
                fecha_inicio=cursor,
                fecha_fin=fin_tramo,
            )
        )
        cursor = fin_tramo
        numero_periodo += 1

    interes_total = money(
        sum((tramo.interes for tramo in tramos), start=Decimal("0.00"))
    )
    return ResultadoInteresCarencia(
        capital_base=capital,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        tasa_anual=tasa_anual,
        modalidad=modalidad,
        convencion=convencion,
        tramos=tuple(tramos),
        interes_total=interes_total,
    )
