"""Escenarios de simulación de un préstamo con carencia inicial.

Este módulo es puro: no crea préstamos ni escribe en SQLite. Distingue el
interés devengado durante la carencia del capital que luego se amortiza. La
capitalización solo se permite mediante una opción explícita de simulación y
el resultado queda marcado como no apto para contratar sin revisión legal.

Limitación deliberada de esta primera versión: la tabla de amortización
posterior utiliza períodos mensuales, igual que el generador actual. Por eso
se exige ConvencionDias.MENSUAL; las convenciones de días reales requieren
extender el generador regular de amortización antes de ofrecerlas como un
contrato integral.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from dateutil.relativedelta import relativedelta

from .amortizacion import generar_tabla
from .carencia import ResultadoInteresCarencia, calcular_interes_carencia_simple
from .excepciones import ErrorCalculo, ErrorValidacion
from .tipos import ConvencionDias, ModalidadTasa, SistemaAmortizacion, money
from .xirr import xirr


class TratamientoCarencia(str, Enum):
    """Tratamientos comparables de los intereses durante la carencia."""

    SIN_INTERES = "SIN_INTERES"
    PAGAR_INTERES_DURANTE_CARENCIA = "PAGAR_INTERES_DURANTE_CARENCIA"
    DIFERIR_SIMPLE_PRIMERA_CUOTA = "DIFERIR_SIMPLE_PRIMERA_CUOTA"
    DIFERIR_SIMPLE_DISTRIBUIDO = "DIFERIR_SIMPLE_DISTRIBUIDO"
    CAPITALIZAR_AL_FIN = "CAPITALIZAR_AL_FIN"


@dataclass(frozen=True, slots=True)
class CuotaCarenciaSimulada:
    """Una cuota posterior a la carencia, con los componentes separados."""

    numero: int
    vencimiento: date
    capital_inicial: Decimal
    interes_periodo: Decimal
    amortizacion_capital: Decimal
    saldo_capital: Decimal
    cuota_base: Decimal
    interes_carencia_agregado: Decimal
    importe_total: Decimal


@dataclass(frozen=True, slots=True)
class ResultadoSimulacionCarencia:
    """Salida completa y fechada para comparar deudor y prestamista."""

    capital_original: Decimal
    fecha_desembolso: date
    fecha_fin_carencia: date
    fecha_primer_vencimiento: date
    meses_carencia: int
    plazo_amortizacion_meses: int
    tasa_anual: Decimal
    modalidad_tasa: ModalidadTasa
    convencion: ConvencionDias
    sistema: SistemaAmortizacion
    tratamiento: TratamientoCarencia
    interes_simple_referencia_carencia: Decimal
    interes_carencia_pagado_durante: Decimal
    interes_carencia_diferido: Decimal
    interes_carencia_capitalizado: Decimal
    interes_carencia_no_cobrado: Decimal
    capital_amortizable_inicio: Decimal
    tramos_carencia: tuple
    cuotas: tuple[CuotaCarenciaSimulada, ...]
    flujos_prestamista: tuple[tuple[date, Decimal], ...]
    rendimiento_anualizado_prestamista: Decimal | None
    total_pagado_deudor: Decimal
    costo_total_intereses_deudor: Decimal
    advertencias: tuple[str, ...]
    solo_analisis: bool


def _distribuir_interes(interes: Decimal, cantidad: int) -> tuple[Decimal, ...]:
    """Distribuye centavos de modo que la suma sea exactamente el interés."""
    if cantidad <= 0:
        raise ErrorValidacion("La cantidad de cuotas debe ser positiva")
    if interes <= 0:
        return tuple(Decimal("0.00") for _ in range(cantidad))
    parte = money(interes / Decimal(cantidad))
    partes = [parte for _ in range(cantidad)]
    partes[-1] = money(interes - sum(partes[:-1], start=Decimal("0.00")))
    return tuple(partes)


def simular_carencia(
    *,
    capital: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    convencion: ConvencionDias,
    fecha_desembolso: date,
    meses_carencia: int,
    plazo_amortizacion_meses: int,
    sistema: SistemaAmortizacion,
    tratamiento: TratamientoCarencia,
    permitir_capitalizacion_solo_analisis: bool = False,
) -> ResultadoSimulacionCarencia:
    """Compara una carencia y el plan de cuotas posterior sin persistir datos.

    Semántica de fechas: la carencia termina al cumplirse el número de meses
    acordado desde el desembolso; la primera cuota regular vence un mes después.
    Así, con 12 meses de carencia desde el 31/01/2026, la carencia finaliza el
    31/01/2027 y el primer vencimiento regular es el 28/02/2027.

    El interés de carencia siempre se calcula sobre capital constante, usando
    la autoridad existente de interés por período. Según el tratamiento, se
    puede no cobrar, cobrar período a período, diferir sin capitalizar o
    capitalizar una sola vez al final (solo escenario explícito).
    """
    if capital <= 0:
        raise ErrorValidacion("El capital debe ser mayor a cero")
    if tasa_anual < 0:
        raise ErrorValidacion("La tasa anual no puede ser negativa")
    if meses_carencia < 0:
        raise ErrorValidacion("Los meses de carencia no pueden ser negativos")
    if plazo_amortizacion_meses <= 0:
        raise ErrorValidacion("El plazo de amortización debe ser mayor a cero")
    if convencion != ConvencionDias.MENSUAL:
        raise ErrorValidacion(
            "La simulación integral actualmente requiere convención MENSUAL, "
            "porque la tabla de amortización posterior todavía no admite "
            "convenciones de días reales. El cálculo aislado de carencia sí "
            "admite esas convenciones."
        )
    if sistema not in {SistemaAmortizacion.FRANCES, SistemaAmortizacion.ALEMAN}:
        raise ErrorValidacion("La amortización posterior debe ser FRANCES o ALEMAN")
    if (
        tratamiento == TratamientoCarencia.CAPITALIZAR_AL_FIN
        and not permitir_capitalizacion_solo_analisis
    ):
        raise ErrorValidacion(
            "La capitalización no se ofrece como modalidad operativa. Para "
            "compararla, activá explícitamente permitir_capitalizacion_solo_analisis."
        )

    if (
        tratamiento == TratamientoCarencia.CAPITALIZAR_AL_FIN
        and modalidad == ModalidadTasa.TEA
    ):
        raise ErrorValidacion(
            "La comparación de capitalización con TEA está deshabilitada hasta "
            "definir una regla contractual de capitalización coherente con una "
            "tasa efectiva anual. Elegí TNA para este escenario o compará las "
            "alternativas no capitalizadas."
        )

    fecha_fin_carencia = fecha_desembolso + relativedelta(months=meses_carencia)
    fecha_primera_cuota = fecha_fin_carencia + relativedelta(months=1)
    referencia = calcular_interes_carencia_simple(
        capital=capital,
        tasa_anual=tasa_anual,
        modalidad=modalidad,
        convencion=convencion,
        fecha_inicio=fecha_desembolso,
        fecha_fin=fecha_fin_carencia,
    )
    interes_referencia = referencia.interes_total
    interes_pagado = Decimal("0.00")
    interes_diferido = Decimal("0.00")
    interes_capitalizado = Decimal("0.00")
    interes_no_cobrado = Decimal("0.00")
    capital_amortizable = capital
    advertencias: list[str] = []
    flujos: list[tuple[date, Decimal]] = [(fecha_desembolso, money(-capital))]

    if tratamiento == TratamientoCarencia.SIN_INTERES:
        interes_no_cobrado = interes_referencia
        if interes_referencia > 0:
            advertencias.append(
                "El prestamista no cobra interés compensatorio durante la "
                "carencia; la cifra de referencia no forma parte de la deuda."
            )
    elif tratamiento == TratamientoCarencia.PAGAR_INTERES_DURANTE_CARENCIA:
        interes_pagado = interes_referencia
        for tramo in referencia.tramos:
            if tramo.interes > 0:
                flujos.append((tramo.fecha_fin, tramo.interes))
    elif tratamiento in {
        TratamientoCarencia.DIFERIR_SIMPLE_PRIMERA_CUOTA,
        TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO,
    }:
        interes_diferido = interes_referencia
    elif tratamiento == TratamientoCarencia.CAPITALIZAR_AL_FIN:
        interes_capitalizado = interes_referencia
        capital_amortizable = money(capital + interes_capitalizado)
        advertencias.append(
            "Escenario exclusivamente comparativo: incorpora el interés al "
            "capital al final de la carencia. Requiere revisar el pacto y su "
            "validez jurídica antes de utilizarse en un préstamo real."
        )

    if modalidad == ModalidadTasa.TEA and tratamiento in {
        TratamientoCarencia.DIFERIR_SIMPLE_PRIMERA_CUOTA,
        TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO,
    }:
        advertencias.append(
            "La TEM equivalente a TEA se aplica sobre capital constante sin "
            "capitalizar el interés diferido. El rendimiento efectivo del "
            "prestamista puede ser inferior a la TEA indicada; revisar la "
            "XIRR de los flujos y la redacción contractual."
        )

    tabla = generar_tabla(
        capital=capital_amortizable,
        tasa_anual=tasa_anual,
        modalidad=modalidad,
        meses=plazo_amortizacion_meses,
        fecha_inicio=fecha_fin_carencia,
        sistema=sistema,
    )

    agregados = [Decimal("0.00") for _ in tabla]
    if tratamiento == TratamientoCarencia.DIFERIR_SIMPLE_PRIMERA_CUOTA:
        agregados[0] = interes_diferido
    elif tratamiento == TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO:
        agregados = list(_distribuir_interes(interes_diferido, len(tabla)))

    cuotas: list[CuotaCarenciaSimulada] = []
    total_pagado = interes_pagado
    for fila, agregado in zip(tabla, agregados):
        importe_total = money(fila["cuota"] + agregado)
        cuota = CuotaCarenciaSimulada(
            numero=fila["numero"],
            vencimiento=fila["vencimiento"],
            capital_inicial=fila["capital_inicial"],
            interes_periodo=fila["interes"],
            amortizacion_capital=fila["capital"],
            saldo_capital=fila["saldo"],
            cuota_base=fila["cuota"],
            interes_carencia_agregado=agregado,
            importe_total=importe_total,
        )
        cuotas.append(cuota)
        flujos.append((cuota.vencimiento, importe_total))
        total_pagado = money(total_pagado + importe_total)

    flujos_ordenados = tuple(sorted(flujos, key=lambda x: x[0]))
    rendimiento: Decimal | None
    try:
        rendimiento = xirr(list(flujos_ordenados))
    except (ErrorCalculo, ErrorValidacion, ArithmeticError, OverflowError):
        rendimiento = None
        advertencias.append(
            "No se pudo obtener una XIRR estable para estos flujos; revisar "
            "fechas, signos y magnitudes antes de interpretar la rentabilidad."
        )

    return ResultadoSimulacionCarencia(
        capital_original=money(capital),
        fecha_desembolso=fecha_desembolso,
        fecha_fin_carencia=fecha_fin_carencia,
        fecha_primer_vencimiento=fecha_primera_cuota,
        meses_carencia=meses_carencia,
        plazo_amortizacion_meses=plazo_amortizacion_meses,
        tasa_anual=tasa_anual,
        modalidad_tasa=modalidad,
        convencion=convencion,
        sistema=sistema,
        tratamiento=tratamiento,
        interes_simple_referencia_carencia=interes_referencia,
        interes_carencia_pagado_durante=interes_pagado,
        interes_carencia_diferido=interes_diferido,
        interes_carencia_capitalizado=interes_capitalizado,
        interes_carencia_no_cobrado=interes_no_cobrado,
        capital_amortizable_inicio=money(capital_amortizable),
        tramos_carencia=referencia.tramos,
        cuotas=tuple(cuotas),
        flujos_prestamista=flujos_ordenados,
        rendimiento_anualizado_prestamista=rendimiento,
        total_pagado_deudor=money(total_pagado),
        costo_total_intereses_deudor=money(total_pagado - capital),
        advertencias=tuple(advertencias),
        solo_analisis=(tratamiento == TratamientoCarencia.CAPITALIZAR_AL_FIN),
    )
