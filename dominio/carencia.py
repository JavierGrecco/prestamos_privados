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
    """Calcula el tramo; ACTUAL_ACTUAL se divide en el cambio de año."""
    if fecha_fin <= fecha_inicio:
        return ()

    if convencion != ConvencionDias.ACTUAL_ACTUAL:
        interes = interes_periodo(
            saldo=capital,
            tasa_anual=tasa_anual,
            modalidad=modalidad,
            convencion=convencion,
            fecha_ini=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        return (
            TramoInteresCarencia(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                capital_base=capital,
                interes=interes,
            ),
        )

    tramos: list[TramoInteresCarencia] = []
    cursor = fecha_inicio
    while cursor < fecha_fin:
        inicio_anio_siguiente = date(cursor.year + 1, 1, 1)
        fin_tramo = min(fecha_fin, inicio_anio_siguiente)
        interes = interes_periodo(
            saldo=capital,
            tasa_anual=tasa_anual,
            modalidad=modalidad,
            convencion=convencion,
            fecha_ini=cursor,
            fecha_fin=fin_tramo,
        )
        tramos.append(
            TramoInteresCarencia(
                fecha_inicio=cursor,
                fecha_fin=fin_tramo,
                capital_base=capital,
                interes=interes,
            )
        )
        cursor = fin_tramo
    return tuple(tramos)


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

    El capital usado para cada tramo permanece constante. Las fechas se
    segmentan por períodos mensuales anclados a la fecha inicial, para que
    un inicio en fin de mes no derive progresivamente del 28/29 al día 28/29.

    Para ACTUAL_ACTUAL, cada tramo también se corta al cambiar de año. El
    interés se redondea según la autoridad existente interes_periodo en cada
    tramo y el resultado suma esos importes. No decide cómo se cobran los
    intereses ni autoriza su capitalización.
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
                "Con convención MENSUAL o 30/360, la carencia debe terminar "
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
