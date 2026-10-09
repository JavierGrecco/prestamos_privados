"""Simulación de un préstamo/un plan de reposición medido en unidades USD.

No crea contratos ni persiste pagos. El cronograma, capital e interés se
calculan en USD de referencia; cada equivalente ARS requiere una cotización
independiente, fechada y etiquetada para esa cuota.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from typing import Mapping

from dateutil.relativedelta import relativedelta

from .amortizacion import fraccion_anual_por_fechas, tasa_periodo_por_fechas
from .carencia import calcular_interes_carencia_simple
from .excepciones import ErrorCalculo, ErrorValidacion
from .simulacion_carencia import (
    ResultadoSimulacionCarencia,
    TratamientoCarencia,
    simular_carencia,
)
from .tipos import ConvencionDias, ModalidadTasa, SistemaAmortizacion, money
from .xirr import xirr


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
        if self.naturaleza not in {"OBSERVADA", "PROYECTADA", "SUPUESTO"}:
            raise ErrorValidacion(
                "La naturaleza de la cotización debe ser OBSERVADA, PROYECTADA o SUPUESTO"
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
    tasa_benchmark_usd: Decimal
    modalidad_benchmark: ModalidadTasa
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
    capital_objetivo_fin_carencia_usd: Decimal
    rendimiento_benchmark_carencia_usd: Decimal
    brecha_rendimiento_benchmark_carencia_usd: Decimal
    modo_reposicion_interna: bool
    total_programado_usd: Decimal
    total_equivalente_ars: Decimal | None
    rendimiento_anualizado_usd: Decimal | None
    cuotas: tuple[CuotaUnidadUsd, ...]
    advertencias: tuple[str, ...]
    solo_analisis: bool = True


def _valor_benchmark_intervalo_usd(
    *,
    capital_usd: Decimal,
    tasa_anual_usd: Decimal,
    modalidad_tasa: ModalidadTasa,
    convencion_dias: ConvencionDias,
    fecha_inicio: date,
    fecha_fin: date,
) -> Decimal:
    """Valor futuro de un importe reinvirtiendo el benchmark entre dos fechas."""
    if fecha_fin < fecha_inicio:
        raise ErrorValidacion("La fecha final del benchmark no puede preceder a la inicial")
    if fecha_fin == fecha_inicio:
        return money(capital_usd)

    valor = Decimal(capital_usd)
    with localcontext() as contexto:
        contexto.prec = 40
        if convencion_dias == ConvencionDias.MENSUAL:
            # La convención mensual cuenta períodos de calendario, no días reales.
            periodos = (
                (fecha_fin.year - fecha_inicio.year) * 12
                + fecha_fin.month - fecha_inicio.month
            )
            for _ in range(periodos):
                factor = tasa_periodo_por_fechas(
                    tasa_anual=tasa_anual_usd,
                    modalidad=modalidad_tasa,
                    fraccion_anual=Decimal("1") / Decimal("12"),
                )
                valor *= Decimal("1") + factor
            return money(valor)

        cursor = fecha_inicio
        numero_periodo = 1
        while cursor < fecha_fin:
            aniversario = fecha_inicio + relativedelta(months=numero_periodo)
            fin_tramo = min(aniversario, fecha_fin)
            if fin_tramo <= cursor:
                raise ErrorValidacion("El calendario del benchmark no avanza")
            fraccion = fraccion_anual_por_fechas(
                cursor,
                fin_tramo,
                convencion_dias,
            )
            factor = tasa_periodo_por_fechas(
                tasa_anual=tasa_anual_usd,
                modalidad=modalidad_tasa,
                fraccion_anual=fraccion,
            )
            valor *= Decimal("1") + factor
            cursor = fin_tramo
            numero_periodo += 1
    return money(valor)



def _fmt_monto(valor: Decimal) -> str:
    return f"{valor:.2f}"


def _advertencia_brecha_benchmark(valor: Decimal) -> str | None:
    if valor > 0:
        return (
            "Durante la carencia, el rendimiento compuesto del benchmark supera "
            f"el interés simple contractual en USD {_fmt_monto(valor)}. "
            "La diferencia es comparativa y no se suma automáticamente a la deuda."
        )
    if valor < 0:
        return (
            "Durante la carencia, el interés simple contractual supera el "
            f"rendimiento compuesto del benchmark en USD {_fmt_monto(abs(valor))}. "
            "Revisá los supuestos antes de interpretar el costo."
        )
    return None


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
    modo_reposicion_interna: bool = False,
    tasa_benchmark_usd: Decimal | None = None,
    modalidad_benchmark: ModalidadTasa | None = None,
    cotizaciones_por_vencimiento: Mapping[date, CotizacionUnidad] | None = None,
) -> ResultadoUnidadUsd:
    """Simula el cronograma en USD y convierte cada cuota por separado.

    El capital ARS inicial se divide por la cotización inicial para fijar las
    unidades USD de referencia. El plan de pagos se calcula sobre esas unidades
    usando una tasa expresada en USD. Las cotizaciones por vencimiento solo
    valúan el pago en ARS: nunca recalculan la deuda ni cambian la cuota USD.

    Para esta primera versión se admiten SIN_INTERES y los dos tratamientos de
    interés simple diferido. Pago de interés durante carencia queda fuera porque
    requiere un calendario de cobros. modo_reposicion_interna calcula por separado
    el valor futuro del capital si el rendimiento del benchmark se reinvierte
    durante la carencia y usa ese valor como base objetivo de amortización; no
    es una cláusula contractual de capitalización. La función no persiste datos.
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
        raise ErrorValidacion("La tasa contractual anual en USD no puede ser negativa")
    tasa_benchmark = (
        tasa_anual_usd if tasa_benchmark_usd is None else tasa_benchmark_usd
    )
    modalidad_bench = modalidad_tasa if modalidad_benchmark is None else modalidad_benchmark
    if tasa_benchmark < 0:
        raise ErrorValidacion("La tasa anual del benchmark en USD no puede ser negativa")
    if modo_reposicion_interna:
        if tratamiento_carencia != TratamientoCarencia.SIN_INTERES:
            raise ErrorValidacion(
                "En el autopréstamo, el rendimiento de carencia ya forma parte "
                "de la base objetivo; use SIN_INTERES para no contarlo dos veces."
            )
        # El plan interno usa el benchmark como rendimiento objetivo en ambas etapas.
        if tasa_anual_usd != tasa_benchmark or modalidad_tasa != modalidad_bench:
            raise ErrorValidacion(
                "En la reposición interna, la tasa de amortización debe coincidir "
                "con el benchmark declarado."
            )
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
    valor_benchmark_fin_carencia = _valor_benchmark_intervalo_usd(
        capital_usd=capital_usd,
        tasa_anual_usd=tasa_benchmark,
        modalidad_tasa=modalidad_bench,
        convencion_dias=convencion_dias,
        fecha_inicio=fecha_desembolso,
        fecha_fin=fecha_fin_carencia,
    )
    rendimiento_benchmark_carencia = money(
        valor_benchmark_fin_carencia - capital_usd
    )
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

    referencia_simple = calcular_interes_carencia_simple(
        capital=capital_usd,
        tasa_anual=tasa_anual_usd,
        modalidad=modalidad_tasa,
        convencion=convencion_dias,
        fecha_inicio=fecha_desembolso,
        fecha_fin=fecha_fin_carencia,
    )
    if modo_reposicion_interna:
        # El rendimiento del benchmark durante la carencia se reinvierte y
        # forma la base objetivo interna. No se suma además como interés simple
        # separado, para no contar dos veces el mismo período.
        simulacion: ResultadoSimulacionCarencia = simular_carencia(
            capital=valor_benchmark_fin_carencia,
            tasa_anual=tasa_anual_usd,
            modalidad=modalidad_tasa,
            convencion=convencion_dias,
            fecha_desembolso=fecha_fin_carencia,
            meses_carencia=0,
            plazo_amortizacion_meses=plazo_amortizacion_meses,
            sistema=sistema,
            tratamiento=TratamientoCarencia.SIN_INTERES,
        )
        interes_referencia_carencia = referencia_simple.interes_total
        interes_debido_carencia = Decimal("0.00")
        interes_no_cobrado_carencia = Decimal("0.00")
        capital_objetivo_fin_carencia = valor_benchmark_fin_carencia
        brecha_rendimiento_carencia = Decimal("0.00")
        flujos_objetivo = [(fecha_desembolso, money(-capital_usd))]
        flujos_objetivo.extend(
            (cuota.vencimiento, cuota.importe_total)
            for cuota in simulacion.cuotas
        )
        try:
            rendimiento_anualizado = xirr(sorted(flujos_objetivo, key=lambda f: f[0]))
        except (ErrorCalculo, ErrorValidacion, ArithmeticError, OverflowError):
            rendimiento_anualizado = None
    else:
        simulacion = simular_carencia(
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
        interes_referencia_carencia = simulacion.interes_simple_referencia_carencia
        interes_debido_carencia = simulacion.interes_carencia_diferido
        interes_no_cobrado_carencia = simulacion.interes_carencia_no_cobrado
        capital_objetivo_fin_carencia = simulacion.capital_amortizable_inicio
        brecha_rendimiento_carencia = money(
            rendimiento_benchmark_carencia - interes_debido_carencia
        )
        rendimiento_anualizado = simulacion.rendimiento_anualizado_prestamista

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
        tasa_benchmark_usd=tasa_benchmark,
        modalidad_benchmark=modalidad_bench,
        convencion_dias=convencion_dias,
        sistema=sistema,
        tratamiento_carencia=tratamiento_carencia,
        fecha_desembolso=fecha_desembolso,
        fecha_fin_carencia=fecha_fin_carencia,
        fecha_primer_vencimiento=fecha_fin_carencia + relativedelta(months=1),
        meses_carencia=meses_carencia,
        plazo_amortizacion_meses=plazo_amortizacion_meses,
        interes_referencia_carencia_usd=interes_referencia_carencia,
        interes_debido_carencia_usd=interes_debido_carencia,
        interes_no_cobrado_carencia_usd=interes_no_cobrado_carencia,
        capital_objetivo_fin_carencia_usd=capital_objetivo_fin_carencia,
        rendimiento_benchmark_carencia_usd=rendimiento_benchmark_carencia,
        brecha_rendimiento_benchmark_carencia_usd=brecha_rendimiento_carencia,
        modo_reposicion_interna=modo_reposicion_interna,
        total_programado_usd=money(sum(
            (cuota.importe_total_usd for cuota in cuotas),
            Decimal("0.00"),
        )),
        total_equivalente_ars=total_equivalente_ars,
        rendimiento_anualizado_usd=rendimiento_anualizado,
        cuotas=tuple(cuotas),
        advertencias=(
            *simulacion.advertencias,
            *(
                ("Plan interno: el rendimiento benchmark durante la carencia se reinvierte y forma la base objetivo; no es una cláusula legal de capitalización.",)
                if modo_reposicion_interna
                else (
                    (_advertencia_brecha_benchmark(brecha_rendimiento_carencia),)
                    if brecha_rendimiento_carencia != Decimal("0.00")
                    else ()
                )
            ),
            "Simulación en unidad USD: no crea un contrato ni habilita pagos en ARS equivalentes.",
            *(
                ("Faltan cotizaciones para una o más cuotas; el total equivalente ARS no está completo.",)
                if not todos_tienen_cotizacion
                else ()
            ),
        ),
        solo_analisis=True,
    )
