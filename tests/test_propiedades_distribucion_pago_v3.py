"""Propiedades matemáticas del reparto V3 por mayores residuos."""

from decimal import Decimal, ROUND_DOWN

from hypothesis import given, settings, strategies as st

from dominio.distribucion_pago_v3 import (
    ParticipacionPagoV3,
    distribuir_pago_v3,
)

UNIDADES_PORCENTAJE = 100_000_000
CENTAVO = Decimal("0.01")


@st.composite
def escenario_distribucion(draw):
    """Genera participaciones que suman exactamente 100% a ocho decimales."""
    cantidad = draw(st.integers(min_value=1, max_value=15))
    cortes = sorted(
        draw(
            st.lists(
                st.integers(min_value=0, max_value=UNIDADES_PORCENTAJE),
                min_size=cantidad - 1,
                max_size=cantidad - 1,
            )
        )
    )
    limites = [0, *cortes, UNIDADES_PORCENTAJE]
    unidades_por_inversor = {
        inversor_id: limites[inversor_id] - limites[inversor_id - 1]
        for inversor_id in range(1, cantidad + 1)
    }

    monto_centavos = draw(st.integers(min_value=1, max_value=10**12))
    orden_ids = draw(st.permutations(tuple(unidades_por_inversor)))
    participaciones = tuple(
        ParticipacionPagoV3(
            inversor_id=inversor_id,
            porcentaje=Decimal(unidades_por_inversor[inversor_id])
            / Decimal(UNIDADES_PORCENTAJE),
        )
        for inversor_id in orden_ids
    )
    monto = Decimal(monto_centavos) / Decimal("100")

    return monto_centavos, monto, participaciones, unidades_por_inversor


@settings(max_examples=250, deadline=None)
@given(escenario_distribucion())
def test_mayores_residuos_conserva_centavos_y_respeta_piso_techo(escenario):
    monto_centavos, monto, participaciones, unidades_por_inversor = escenario

    asignaciones = distribuir_pago_v3(monto, participaciones)
    por_inversor = {asignacion.inversor_id: asignacion.monto for asignacion in asignaciones}

    assert len(por_inversor) == len(unidades_por_inversor)
    assert sum(por_inversor.values(), Decimal("0.00")) == monto
    assert all(
        importe >= Decimal("0.00") and importe == importe.quantize(CENTAVO)
        for importe in por_inversor.values()
    )

    for inversor_id, unidades in unidades_por_inversor.items():
        proporcion_exacta_en_centavos = (
            Decimal(monto_centavos) * Decimal(unidades)
            / Decimal(UNIDADES_PORCENTAJE)
        )
        piso = int(
            proporcion_exacta_en_centavos.to_integral_value(rounding=ROUND_DOWN)
        )
        techo = piso if proporcion_exacta_en_centavos == Decimal(piso) else piso + 1
        centavos_asignados = int(por_inversor[inversor_id] / CENTAVO)

        assert centavos_asignados in (piso, techo)


@settings(max_examples=250, deadline=None)
@given(escenario_distribucion())
def test_reparto_no_depende_del_orden_de_entrada(escenario):
    _, monto, participaciones, _ = escenario

    original = {
        asignacion.inversor_id: asignacion.monto
        for asignacion in distribuir_pago_v3(monto, participaciones)
    }
    invertido = {
        asignacion.inversor_id: asignacion.monto
        for asignacion in distribuir_pago_v3(monto, tuple(reversed(participaciones)))
    }

    assert original == invertido
