"""Simulación de un préstamo/un plan de reposición medido en unidades USD.

No crea contratos ni persiste pagos. El cronograma, capital e interés se
calculan en USD de referencia; cada equivalente ARS requiere una cotización
independiente, fechada y etiquetada para esa cuota.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping

from dateutil.relativedelta import relativedelta

from .excepciones import ErrorValidacion
from .simulacion_carencia import (
    ResultadoSimulacionCarencia,
    TratamientoCarencia,
    simular_carencia,
)
from .tipos import ConvencionDias, ModalidadTasa, SistemaAmortizacion, money


TRATAMIENTOS_UNIDAD_USD_ADMITIDOS = frozenset({
    TratamientoCarencia.SIN_INTERES,
    TratamientoCarencia.DIFERIR_SIMPLE_PRIMERA_CUOTA,
    TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO,
})


@dataclass(frozen=True, slots=True)
class CotizacionUnidad:
    """Cotización ARS por USD usada para originación o escenario de cuota.

    naturaleza puede ser OBSERVADA o PROYECTADA. fuente y lado deben describir
    el origen de forma reproducible (p. ej. un proveedor/instrumento y su lado
    vendedor). La referencia opcional puede contener URL o nota de evidencia.
    """

    fecha_cotizacion: date
    ars_por_usd: Decimal
    fuente: str
    lado: str
    naturaleza: str = "OBSERVADA"
    referencia: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.fecha_cotizacion, date):
            raise ErrorValidacion("La fecha de cotización debe ser una fecha")
        if not isinstance(self.ars_por_usd, Decimal):
            raise ErrorValidacion("La cotización debe representarse con Decimal")
        if self.ars_por_usd <= 0:
            raise ErrorValidacion("La cotización debe ser mayor a cero ARS por USD")
        if not self.fuente or not self.fuente.strip():
            raise ErrorValidacion("La fuente de cotización es obligatoria")
        if not self.lado or not self.lado.strip():
            raise ErrorValidacion("El lado de la cotización es obligatorio")
        if self.naturaleza not in {"OBSERVADA", "PROYECTADA"}:
            raise ErrorValidacion(
                "La naturaleza de la cotización debe ser OBSERVADA o PROYECTADA"
            )


@dataclass(frozen=True, slots=True)
class CuotaUnidadUsd:
    """Cuota calculada en USD y valuación ARS separada."""

    numero: int
    fecha_vencimiento: date
    capital_inicial_usd: Decimal
    interes_periodo_usd: Decimal
    amortizacion_capital_usd: Decimal
    saldo_capital_usd: Decimal
    cuota_base_usd: Decimal
    interes_carencia_usd: Decimal
    importe_total_usd: Decimal
    cotizacion: CotizacionUnidad | None
    equivalente_ars: Decimal | None


@dataclass(frozen=True, slots=True)
class ResultadoUnidadUsd:
    """Resultado analítico; no equivale a contrato ni a pago persistido."""

    capital_desembolso_ars: Decimal
    cotizacion_inicial: CotizacionUnidad
    capital_inicial_usd: Decimal
    tasa_anual_usd: Decimal
    modalidad_tasa: ModalidadTasa
    convencion_dias: ConvencionDias
    sistema: SistemaAmortizacion
    tratamiento_carencia: TratamientoCarencia
    fecha_desembolso: date
    fecha_fin_carencia: date
    fecha_primer_vencimiento: date
    meses_carencia: int
    plazo_amortizacion_meses: int
    interes_referencia_carencia_usd: Decimal
    interes_debido_carencia_usd: Decimal
    interes_no_cobrado_carencia_usd: Decimal
    total_programado_usd: Decimal
    total_equivalente_ars: Decimal | None
    rendimiento_anualizado_usd: Decimal | None
    cuotas: tuple[CuotaUnidadUsd, ...]
    advertencias: tuple[str, ...]
    solo_analisis: bool = True


def simular_unidad_usd(
    *,
    capital_desembolso_ars: Decimal,
    cotizacion_inicial: CotizacionUnidad,
    tasa_anual_usd: Decimal,
    modalidad_tasa: ModalidadTasa,
    convencion_dias: ConvencionDias,
    sistema: SistemaAmortizacion,
    fecha_desembolso: date,
    meses_carencia: int,
    plazo_amortizacion_meses: int,
    tratamiento_carencia: TratamientoCarencia,
    cotizaciones_por_vencimiento: Mapping[date, CotizacionUnidad] | None = None,
) -> ResultadoUnidadUsd:
    """Simula el cronograma en USD y convierte cada cuota por separado.

    El capital ARS inicial se divide por la cotización inicial para fijar las
    unidades USD de referencia. El plan de pagos se calcula sobre esas unidades
    usando una tasa expresada en USD. Las cotizaciones por vencimiento solo
    valúan el pago en ARS: nunca recalculan la deuda ni cambian la cuota USD.

    Para esta primera versión se admiten SIN_INTERES y los dos tratamientos de
    interés simple diferido. Pago de interés durante carencia y capitalización
    quedan fuera; requieren un calendario de cobros durante la carencia o una
    regla contractual específica. La función es de análisis y no persiste datos.
    """
    if capital_desembolso_ars <= 0:
        raise ErrorValidacion("El capital de desembolso debe ser mayor a cero")
    if cotizacion_inicial.ars_por_usd <= 0:
        raise ErrorValidacion("La cotización inicial debe ser mayor a cero")
    if cotizacion_inicial.fecha_cotizacion > fecha_desembolso:
        raise ErrorValidacion(
            "La cotización inicial no puede ser posterior al desembolso"
        )
    if tasa_anual_usd < 0:
        raise ErrorValidacion("La tasa anual en USD no puede ser negativa")
    if meses_carencia < 0:
        raise ErrorValidacion("Los meses de carencia no pueden ser negativos")
    if plazo_amortizacion_meses <= 0:
        raise ErrorValidacion("El plazo de amortización debe ser mayor a cero")
    if tratamiento_carencia not in TRATAMIENTOS_UNIDAD_USD_ADMITIDOS:
        raise ErrorValidacion(
            "Esta simulación admite SIN_INTERES, DIFERIR_SIMPLE_PRIMERA_CUOTA "
            "o DIFERIR_SIMPLE_DISTRIBUIDO. El pago durante la carencia y la "
            "capitalización necesitan una entrega específica."
        )
    if sistema not in {SistemaAmortizacion.FRANCES, SistemaAmortizacion.ALEMAN}:
        raise ErrorValidacion("El sistema debe ser FRANCES o ALEMAN")

    capital_usd = money(
        Decimal(str(capital_desembolso_ars)) / cotizacion_inicial.ars_por_usd
    )
    if capital_usd <= 0:
        raise ErrorValidacion(
            "El capital convertido es menor a un centavo USD; revise el importe "
            "o use una unidad de precisión superior en una versión futura"
        )

    fecha_fin_carencia = fecha_desembolso + relativedelta(months=meses_carencia)
    fechas_vencimiento = tuple(
        fecha_fin_carencia + relativedelta(months=numero)
        for numero in range(1, plazo_amortizacion_meses + 1)
    )
    cotizaciones = dict(cotizaciones_por_vencimiento or {})
    if any(not isinstance(fecha, date) for fecha in cotizaciones):
        raise ErrorValidacion(
            "Cada clave de cotización debe ser una fecha de vencimiento"
        )
    if any(not isinstance(cotizacion, CotizacionUnidad) for cotizacion in cotizaciones.values()):
        raise ErrorValidacion(
            "Cada cotización por vencimiento debe ser una CotizacionUnidad validada"
        )
    fechas_desconocidas = set(cotizaciones) - set(fechas_vencimiento)
    if fechas_desconocidas:
        fecha_invalida = min(fechas_desconocidas)
        raise ErrorValidacion(
            f"La fecha {fecha_invalida.isoformat()} no corresponde a un vencimiento"
        )

    simulacion: ResultadoSimulacionCarencia = simular_carencia(
        capital=capital_usd,
        tasa_anual=tasa_anual_usd,
        modalidad=modalidad_tasa,
        convencion=convencion_dias,
        fecha_desembolso=fecha_desembolso,
        meses_carencia=meses_carencia,
        plazo_amortizacion_meses=plazo_amortizacion_meses,
        sistema=sistema,
        tratamiento=tratamiento_carencia,
    )

    cuotas: list[CuotaUnidadUsd] = []
    for cuota in simulacion.cuotas:
        cotizacion = cotizaciones.get(cuota.vencimiento)
        equivalente_ars = (
            money(cuota.importe_total * cotizacion.ars_por_usd)
            if cotizacion is not None
            else None
        )
        cuotas.append(
            CuotaUnidadUsd(
                numero=cuota.numero,
                fecha_vencimiento=cuota.vencimiento,
                capital_inicial_usd=cuota.capital_inicial,
                interes_periodo_usd=cuota.interes_periodo,
                amortizacion_capital_usd=cuota.amortizacion_capital,
                saldo_capital_usd=cuota.saldo_capital,
                cuota_base_usd=cuota.cuota_base,
                interes_carencia_usd=cuota.interes_carencia_agregado,
                importe_total_usd=cuota.importe_total,
                cotizacion=cotizacion,
                equivalente_ars=equivalente_ars,
            )
        )

    todos_tienen_cotizacion = all(c.cotizacion is not None for c in cuotas)
    total_equivalente_ars = (
        money(sum(
            (c.equivalente_ars for c in cuotas if c.equivalente_ars is not None),
            Decimal("0.00"),
        ))
        if todos_tienen_cotizacion
        else None
    )

    return ResultadoUnidadUsd(
        capital_desembolso_ars=money(capital_desembolso_ars),
        cotizacion_inicial=cotizacion_inicial,
        capital_inicial_usd=capital_usd,
        tasa_anual_usd=tasa_anual_usd,
        modalidad_tasa=modalidad_tasa,
        convencion_dias=convencion_dias,
        sistema=sistema,
        tratamiento_carencia=tratamiento_carencia,
        fecha_desembolso=fecha_desembolso,
        fecha_fin_carencia=simulacion.fecha_fin_carencia,
        fecha_primer_vencimiento=simulacion.fecha_primer_vencimiento,
        meses_carencia=meses_carencia,
        plazo_amortizacion_meses=plazo_amortizacion_meses,
        interes_referencia_carencia_usd=simulacion.interes_simple_referencia_carencia,
        interes_debido_carencia_usd=simulacion.interes_carencia_diferido,
        interes_no_cobrado_carencia_usd=simulacion.interes_carencia_no_cobrado,
        total_programado_usd=simulacion.total_pagado_deudor,
        total_equivalente_ars=total_equivalente_ars,
        rendimiento_anualizado_usd=simulacion.rendimiento_anualizado_prestamista,
        cuotas=tuple(cuotas),
        advertencias=(
            *simulacion.advertencias,
            "Simulación en unidad USD: no crea un contrato ni habilita pagos en ARS equivalentes.",
            *(
                ("Faltan cotizaciones para una o más cuotas; el total equivalente ARS no está completo.",)
                if not todos_tienen_cotizacion
                else ()
            ),
        ),
        solo_analisis=True,
    )
