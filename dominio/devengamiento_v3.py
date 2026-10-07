"""Cálculo puro de devengamientos V3-B.

Este módulo convierte una política explícita (tasa + modalidad + convención)
en un Devengamiento reproducible. No consulta reloj, DB ni UI.

Importante: este módulo NO decide todavía si un préstamo francés debe cobrar
"interés adicional" por capital atrasado. Solo resuelve el cálculo temporal
sobre una base financiera ya determinada.
"""
from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext

from .excepciones import ErrorInvariante, ErrorValidacion
from .motor_pagos_v3 import Devengamiento, ZERO
from .tipos import ConceptoImputacion, ConvencionDias, ModalidadTasa, money, rate

DAYS_PER_YEAR_360 = Decimal("360")
DAYS_PER_YEAR_365 = Decimal("365")
TWELVE = Decimal("12")


@dataclass(frozen=True)
class PoliticaInteres:
    """Parámetros suficientes para un devengamiento de interés."""

    tasa_anual: Decimal
    modalidad_tasa: ModalidadTasa
    convencion_dias: ConvencionDias
    concepto: ConceptoImputacion = ConceptoImputacion.INTERES
    origen: str = "INTERES_DEVENGADO"

    def __post_init__(self) -> None:
        tasa = rate(self.tasa_anual)
        if tasa < ZERO:
            raise ErrorValidacion("La tasa anual no puede ser negativa")
        if self.modalidad_tasa not in set(ModalidadTasa):
            raise ErrorValidacion("Modalidad de tasa inválida")
        if self.convencion_dias not in set(ConvencionDias):
            raise ErrorValidacion("Convención de días inválida")
        if not self.origen:
            raise ErrorValidacion("La política debe indicar el origen")
        object.__setattr__(self, "tasa_anual", tasa)


def calcular_devengamiento_interes(
    *,
    base: Decimal,
    fecha_desde: date,
    fecha_hasta: date,
    politica: PoliticaInteres,
    referencia: str | None = None,
) -> Devengamiento:
    """Calcula un devengamiento de interés sin efectos secundarios.

    Intervalo temporal: [fecha_desde, fecha_hasta). Por lo tanto,
    fecha_hasta - fecha_desde es la cantidad de días reales cuando aplica.

    MENSUAL no inventa una fracción para períodos parciales: exige meses
    completos (mismo día o ambos cierres de mes). Esto evita convertir
    silenciosamente 15 días en 15/30 de mes cuando el contrato dice que la
    convención es mensual.
    """
    base = money(base)
    if base < ZERO:
        raise ErrorValidacion("La base del interés no puede ser negativa")
    if fecha_hasta < fecha_desde:
        raise ErrorValidacion("La fecha hasta no puede ser anterior a la fecha desde")

    dias, fraccion_anual = _fraccion_anual(
        fecha_desde, fecha_hasta, politica.convencion_dias
    )

    factor = _factor_tasa(politica.tasa_anual, politica.modalidad_tasa, fraccion_anual)
    with localcontext() as ctx:
        ctx.prec = 34
        interes = base * factor
    interes = money(interes)

    return Devengamiento(
        concepto=politica.concepto,
        monto=interes,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        origen=politica.origen,
        referencia=referencia,
        base=base,
        tasa_anual=politica.tasa_anual,
        modalidad_tasa=politica.modalidad_tasa,
        convencion_dias=politica.convencion_dias,
        dias=dias,
        fraccion_anual=fraccion_anual,
    )


def calcular_interes(
    *,
    base: Decimal,
    fecha_desde: date,
    fecha_hasta: date,
    politica: PoliticaInteres,
) -> Decimal:
    """Atajo puro cuando solo se necesita el monto."""
    return calcular_devengamiento_interes(
        base=base,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        politica=politica,
    ).monto


def calcular_dias(
    fecha_desde: date,
    fecha_hasta: date,
    convencion: ConvencionDias,
) -> int:
    """Devuelve días según la convención para auditoría y pruebas."""
    dias, _ = _fraccion_anual(fecha_desde, fecha_hasta, convencion)
    return dias


def calcular_fraccion_anual(
    fecha_desde: date,
    fecha_hasta: date,
    convencion: ConvencionDias,
) -> Decimal:
    """Devuelve la fracción de año usada por la tasa efectiva/nominal."""
    _, fraccion = _fraccion_anual(fecha_desde, fecha_hasta, convencion)
    return fraccion


def _fraccion_anual(
    fecha_desde: date,
    fecha_hasta: date,
    convencion: ConvencionDias,
) -> tuple[int, Decimal]:
    if fecha_hasta < fecha_desde:
        raise ErrorValidacion("El período de devengamiento es inválido")
    if fecha_hasta == fecha_desde:
        return 0, ZERO

    if convencion is ConvencionDias.MENSUAL:
        meses = _meses_completos(fecha_desde, fecha_hasta)
        return meses * 30, Decimal(meses) / TWELVE

    if convencion is ConvencionDias.ACTUAL_365:
        dias = (fecha_hasta - fecha_desde).days
        return dias, Decimal(dias) / DAYS_PER_YEAR_365

    if convencion is ConvencionDias.ACTUAL_360:
        dias = (fecha_hasta - fecha_desde).days
        return dias, Decimal(dias) / DAYS_PER_YEAR_360

    if convencion is ConvencionDias.TREINTA_360:
        dias = _dias_30e_360(fecha_desde, fecha_hasta)
        return dias, Decimal(dias) / DAYS_PER_YEAR_360

    if convencion is ConvencionDias.ACTUAL_ACTUAL:
        dias = (fecha_hasta - fecha_desde).days
        return dias, _fraccion_actual_actual(fecha_desde, fecha_hasta)

    raise ErrorValidacion(f"Convención no soportada: {convencion}")


def _meses_completos(desde: date, hasta: date) -> int:
    meses = (hasta.year - desde.year) * 12 + (hasta.month - desde.month)
    mismo_dia = hasta.day == desde.day
    ambos_fin_mes = (
        desde.day == monthrange(desde.year, desde.month)[1]
        and hasta.day == monthrange(hasta.year, hasta.month)[1]
    )
    if not (mismo_dia or ambos_fin_mes):
        raise ErrorValidacion(
            "Convención MENSUAL requiere meses completos: mismo día o ambos cierres de mes"
        )
    if meses <= 0:
        raise ErrorInvariante("El período positivo mensual produjo cero meses")
    return meses


def _dias_30e_360(desde: date, hasta: date) -> int:
    d1 = min(desde.day, 30)
    d2 = min(hasta.day, 30)
    return (
        360 * (hasta.year - desde.year)
        + 30 * (hasta.month - desde.month)
        + (d2 - d1)
    )


def _fraccion_actual_actual(desde: date, hasta: date) -> Decimal:
    """Actual/Actual simple por tramos de año calendario."""
    if hasta <= desde:
        return ZERO
    cursor = desde
    fraccion = ZERO
    while cursor < hasta:
        siguiente_ano = date(cursor.year + 1, 1, 1)
        fin = min(hasta, siguiente_ano)
        dias = Decimal((fin - cursor).days)
        dias_ano = Decimal(366 if _es_bisiesto(cursor.year) else 365)
        fraccion += dias / dias_ano
        cursor = fin
    return fraccion


def _es_bisiesto(ano: int) -> bool:
    return ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0)


def _factor_tasa(
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    fraccion_anual: Decimal,
) -> Decimal:
    tasa_anual = rate(tasa_anual)
    if fraccion_anual < ZERO:
        raise ErrorInvariante("La fracción anual no puede ser negativa")
    if fraccion_anual == ZERO or tasa_anual == ZERO:
        return ZERO

    with localcontext() as ctx:
        ctx.prec = 34
        if modalidad is ModalidadTasa.TNA:
            return tasa_anual * fraccion_anual
        if modalidad is ModalidadTasa.TEA:
            return (Decimal("1") + tasa_anual) ** fraccion_anual - Decimal("1")
    raise ErrorValidacion(f"Modalidad no soportada: {modalidad}")
