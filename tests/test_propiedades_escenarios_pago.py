"""Propiedades del simulador puro que prepara pagos Legacy."""

from decimal import Decimal

from hypothesis import given, settings, strategies as st

from dominio.escenarios_pago import DeudaPago, simular_pago
from dominio.tipos import ConceptoImputacion, money

CENTAVO = Decimal("0.01")
ORDENES_WATERFALL = st.permutations(
    (
        ConceptoImputacion.MORA,
        ConceptoImputacion.INTERES,
        ConceptoImputacion.CAPITAL,
    )
)


@st.composite
def escenario_pago_legacy(draw):
    """Genera deudas y pagos monetarios exactos, sin inventar políticas."""
    campos_centavos = {
        nombre: draw(st.integers(min_value=0, max_value=10**10))
        for nombre in (
            "cuota_interes",
            "cuota_capital",
            "arrastre_interes",
            "arrastre_capital",
            "arrastre_mora",
            "interes_extra",
            "mora_nueva",
        )
    }
    deuda = DeudaPago(
        **{
            nombre: Decimal(centavos) / Decimal(100)
            for nombre, centavos in campos_centavos.items()
        }
    )
    total_centavos = sum(campos_centavos.values())
    monto_centavos = draw(
        st.integers(min_value=1, max_value=max(1, total_centavos * 2 + 1))
    )
    tasa_unidades = draw(st.one_of(st.none(), st.integers(min_value=0, max_value=10_000_000)))
    tasa_mensual = (
        None
        if tasa_unidades is None
        else Decimal(tasa_unidades) / Decimal(100_000_000)
    )
    orden = draw(ORDENES_WATERFALL)

    return (
        deuda,
        Decimal(monto_centavos) / Decimal(100),
        tasa_mensual,
        orden,
    )


@settings(max_examples=300, deadline=None)
@given(escenario_pago_legacy())
def test_simulacion_legacy_conserva_el_pago_y_no_sobregira_conceptos(escenario):
    deuda, monto, tasa_mensual, orden = escenario

    resultado = simular_pago(
        monto=monto,
        deuda=deuda,
        tasa_mensual=tasa_mensual,
        orden_imputacion=orden,
    )

    por_concepto = {
        ConceptoImputacion.MORA: (
            resultado.aplicado_mora,
            deuda.deuda_mora,
        ),
        ConceptoImputacion.INTERES: (
            resultado.aplicado_interes,
            deuda.deuda_interes,
        ),
        ConceptoImputacion.CAPITAL: (
            resultado.aplicado_capital,
            deuda.deuda_capital,
        ),
    }
    total_aplicado = sum(
        (aplicado for aplicado, _ in por_concepto.values()),
        Decimal("0.00"),
    )

    assert total_aplicado + resultado.excedente == monto
    assert total_aplicado == min(monto, deuda.total)
    assert resultado.faltante == max(Decimal("0.00"), deuda.total - monto)
    assert resultado.excedente == max(Decimal("0.00"), monto - deuda.total)

    for aplicado, saldo in por_concepto.values():
        assert Decimal("0.00") <= aplicado <= saldo
        assert aplicado == aplicado.quantize(CENTAVO)

    if resultado.excedente > 0:
        assert resultado.tipo == "ADELANTO"
    elif resultado.faltante > 0:
        assert resultado.tipo == "PARCIAL"
    else:
        assert resultado.tipo == "CUOTA"


@settings(max_examples=300, deadline=None)
@given(escenario_pago_legacy())
def test_simulacion_legacy_conserva_desglose_de_capital_y_proyeccion(escenario):
    deuda, monto, tasa_mensual, orden = escenario

    resultado = simular_pago(
        monto=monto,
        deuda=deuda,
        tasa_mensual=tasa_mensual,
        orden_imputacion=orden,
    )

    capital_aplicado_arrastre = min(
        resultado.aplicado_capital,
        deuda.arrastre_capital,
    )
    capital_aplicado_objetivo = money(
        resultado.aplicado_capital - capital_aplicado_arrastre
    )
    arrastre_posterior = money(
        deuda.arrastre_capital - capital_aplicado_arrastre
    )
    objetivo_posterior = money(
        deuda.cuota_capital - capital_aplicado_objetivo
    )
    capital_posterior = money(arrastre_posterior + objetivo_posterior)

    assert resultado.capital_pendiente_despues == capital_posterior

    if tasa_mensual is None or capital_posterior == 0:
        interes_total_esperado = Decimal("0.00")
        interes_generado_esperado = Decimal("0.00")
    else:
        interes_total_esperado = money(capital_posterior * tasa_mensual)
        interes_generado_esperado = money(objetivo_posterior * tasa_mensual)

    assert (
        resultado.interes_extra_estimado_proximo_periodo
        == interes_total_esperado
    )
    assert resultado.interes_extra_generado_por_pago == interes_generado_esperado
    assert (
        resultado.interes_extra_generado_por_pago
        <= resultado.interes_extra_estimado_proximo_periodo
    )
