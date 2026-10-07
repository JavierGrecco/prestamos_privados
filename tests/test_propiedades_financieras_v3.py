"""Property-based tests for the pure V3 financial core.

These tests intentionally stay outside persistence. Their job is to exercise
large families of valid inputs and protect mathematical/algorithmic
invariants of devengamiento and waterfall calculations.
"""
from datetime import date, timedelta
from decimal import Decimal

from hypothesis import assume, given, settings, strategies as st

from dominio.devengamiento_v3 import (
    PoliticaInteres,
    calcular_devengamiento_interes,
)
from dominio.motor_pagos_v3 import (
    ObligacionSnapshot,
    SaldoObligacion,
    calcular_plan_pago,
)
from dominio.tipos import ConvencionDias, ModalidadTasa


MONEY_CENTS = st.integers(min_value=1, max_value=1_000_000)
COMPONENT_CENTS = st.integers(min_value=0, max_value=250_000)


@st.composite
def obligaciones_y_pago(draw):
    componentes = draw(
        st.lists(
            st.tuples(COMPONENT_CENTS, COMPONENT_CENTS, COMPONENT_CENTS),
            min_size=1,
            max_size=5,
        )
    )

    obligaciones = []
    total = 0
    for numero, (mora, interes, capital) in enumerate(componentes, start=1):
        subtotal = mora + interes + capital
        if subtotal == 0:
            capital = 1
            subtotal = 1

        total += subtotal
        obligaciones.append(
            ObligacionSnapshot(
                cuota_id=numero,
                numero_cuota=numero,
                vencimiento=date(2026, 1, 1) + timedelta(days=30 * (numero - 1)),
                estado="PENDIENTE",
                tuvo_pago_parcial=False,
                saldo=SaldoObligacion(
                    mora=Decimal(mora) / Decimal(100),
                    interes=Decimal(interes) / Decimal(100),
                    capital=Decimal(capital) / Decimal(100),
                ),
            )
        )

    porcentaje = draw(st.integers(min_value=1, max_value=10_000))
    monto_centavos = max(1, (total * porcentaje) // 10_000)

    return tuple(obligaciones), Decimal(monto_centavos) / Decimal(100)


@settings(max_examples=100, deadline=None)
@given(obligaciones_y_pago())
def test_waterfall_conserva_dinero_y_es_determinista(data):
    obligaciones, monto = data

    plan_a = calcular_plan_pago(
        prestamo_id=1,
        fecha_valor=date(2026, 1, 1),
        revision_prestamo=0,
        monto_recibido=monto,
        obligaciones=obligaciones,
    )
    plan_b = calcular_plan_pago(
        prestamo_id=1,
        fecha_valor=date(2026, 1, 1),
        revision_prestamo=0,
        monto_recibido=monto,
        obligaciones=obligaciones,
    )

    assert plan_a == plan_b
    assert plan_a.monto_aplicado + plan_a.excedente.monto == monto
    assert plan_a.excedente.monto >= 0
    assert all(aplicacion.monto > 0 for aplicacion in plan_a.aplicaciones)

    for obligacion in plan_a.obligaciones_afectadas:
        assert obligacion.saldo_posterior.total >= 0

        if obligacion.aplicado_interes > 0:
            assert obligacion.saldo_posterior.mora == Decimal("0.00")

        if obligacion.aplicado_capital > 0:
            assert obligacion.saldo_posterior.mora == Decimal("0.00")
            assert obligacion.saldo_posterior.interes == Decimal("0.00")

    numeros = [o.numero_cuota for o in plan_a.obligaciones_afectadas]
    assert numeros == sorted(numeros)

    for anterior, posterior in zip(
        plan_a.obligaciones_afectadas,
        plan_a.obligaciones_afectadas[1:],
    ):
        assert anterior.saldo_posterior.total == Decimal("0.00")


@st.composite
def periodo_real(draw):
    inicio = draw(st.dates(min_value=date(2024, 1, 1), max_value=date(2026, 10, 1)))
    dias_1 = draw(st.integers(min_value=1, max_value=120))
    dias_2 = draw(st.integers(min_value=1, max_value=120))
    medio = inicio + timedelta(days=dias_1)
    fin = medio + timedelta(days=dias_2)
    assume(fin <= date(2027, 12, 31))
    return inicio, medio, fin


def _politica(modalidad: ModalidadTasa) -> PoliticaInteres:
    return PoliticaInteres(
        tasa_anual=Decimal("0.30"),
        modalidad_tasa=modalidad,
        convencion_dias=ConvencionDias.ACTUAL_365,
    )


@settings(max_examples=100, deadline=None)
@given(periodo_real())
def test_tna_es_aditiva_por_segmentos_hasta_el_redondeo(data):
    inicio, medio, fin = data
    politica = _politica(ModalidadTasa.TNA)
    base = Decimal("100000.00")

    directo = calcular_devengamiento_interes(
        base=base,
        fecha_desde=inicio,
        fecha_hasta=fin,
        politica=politica,
    ).monto

    por_segmentos = (
        calcular_devengamiento_interes(
            base=base,
            fecha_desde=inicio,
            fecha_hasta=medio,
            politica=politica,
        ).monto
        + calcular_devengamiento_interes(
            base=base,
            fecha_desde=medio,
            fecha_hasta=fin,
            politica=politica,
        ).monto
    )

    assert abs(directo - por_segmentos) <= Decimal("0.01")


@settings(max_examples=100, deadline=None)
@given(periodo_real())
def test_tea_es_multiplicativa_por_segmentos_hasta_el_redondeo(data):
    inicio, medio, fin = data
    politica = _politica(ModalidadTasa.TEA)
    base = Decimal("100000.00")

    interes_directo = calcular_devengamiento_interes(
        base=base,
        fecha_desde=inicio,
        fecha_hasta=fin,
        politica=politica,
    ).monto

    interes_primera_etapa = calcular_devengamiento_interes(
        base=base,
        fecha_desde=inicio,
        fecha_hasta=medio,
        politica=politica,
    ).monto
    interes_segunda_etapa = calcular_devengamiento_interes(
        base=base + interes_primera_etapa,
        fecha_desde=medio,
        fecha_hasta=fin,
        politica=politica,
    ).monto

    compuesto = interes_primera_etapa + interes_segunda_etapa

    assert abs(interes_directo - compuesto) <= Decimal("0.02")


@settings(max_examples=100, deadline=None)
@given(
    st.dates(min_value=date(2024, 1, 1), max_value=date(2027, 12, 1)),
    st.integers(min_value=1, max_value=365),
)
def test_actual_365_reporta_exactamente_los_dias_reales(inicio, dias):
    fin = inicio + timedelta(days=dias)
    assume(fin <= date.max)

    politica = _politica(ModalidadTasa.TNA)
    dev = calcular_devengamiento_interes(
        base=Decimal("10000.00"),
        fecha_desde=inicio,
        fecha_hasta=fin,
        politica=politica,
    )

    assert dev.dias == dias
    assert dev.fraccion_anual == Decimal(dias) / Decimal(365)
    assert dev.monto >= Decimal("0.00")
