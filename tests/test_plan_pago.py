"""Pruebas del plan puro que comparte simulación y registro."""
from decimal import Decimal

from dominio.plan_pago import CuotaParaPago, planificar_pago


def cuotas_prueba():
    return [
        CuotaParaPago(
            id=1,
            numero=1,
            estado="PENDIENTE",
            interes_pendiente=Decimal("40000"),
            capital_pendiente=Decimal("60000"),
            mora_pendiente=Decimal("0"),
            fue_mora=False,
            tuvo_pago_parcial=False,
            fue_recalculada=False,
        ),
        CuotaParaPago(
            id=2,
            numero=2,
            estado="PENDIENTE",
            interes_pendiente=Decimal("38000"),
            capital_pendiente=Decimal("62000"),
            mora_pendiente=Decimal("0"),
            fue_mora=False,
            tuvo_pago_parcial=False,
            fue_recalculada=False,
        ),
    ]


def test_plan_y_resultado_comparten_el_mismo_waterfall():
    plan = planificar_pago(
        monto=Decimal("50000"),
        cuotas=cuotas_prueba(),
        cuota_objetivo_id=1,
        cuota_interes=Decimal("40000"),
        cuota_capital=Decimal("60000"),
        tasa_mensual=Decimal("0.025"),
        arrastre_interes=Decimal("0"),
        arrastre_capital=Decimal("0"),
        arrastre_mora=Decimal("0"),
        interes_extra=Decimal("0"),
        mora_nueva=Decimal("0"),
    )

    assert plan.resultado.aplicado_interes == Decimal("40000.00")
    assert plan.resultado.aplicado_capital == Decimal("10000.00")
    assert plan.monto_a_capital == Decimal("0.00")
    assert plan.actualizaciones[0].estado == "PARCIAL"
    assert plan.actualizaciones[0].interes_pendiente == Decimal("0.00")
    assert plan.actualizaciones[0].capital_pendiente == Decimal("50000.00")


def test_plan_con_arrastre_actualiza_primero_las_cuotas_anteriores():
    cuotas = [
        CuotaParaPago(
            id=1,
            numero=1,
            estado="PARCIAL",
            interes_pendiente=Decimal("10000"),
            capital_pendiente=Decimal("50000"),
            mora_pendiente=Decimal("0"),
            fue_mora=True,
            tuvo_pago_parcial=True,
            fue_recalculada=False,
        ),
        CuotaParaPago(
            id=2,
            numero=2,
            estado="PENDIENTE",
            interes_pendiente=Decimal("40000"),
            capital_pendiente=Decimal("60000"),
            mora_pendiente=Decimal("0"),
            fue_mora=False,
            tuvo_pago_parcial=False,
            fue_recalculada=False,
        ),
    ]

    plan = planificar_pago(
        monto=Decimal("30000"),
        cuotas=cuotas,
        cuota_objetivo_id=2,
        cuota_interes=Decimal("40000"),
        cuota_capital=Decimal("60000"),
        tasa_mensual=Decimal("0.025"),
        arrastre_interes=Decimal("10000"),
        arrastre_capital=Decimal("50000"),
        arrastre_mora=Decimal("0"),
        interes_extra=Decimal("1250"),
        mora_nueva=Decimal("0"),
    )

    assert plan.resultado.aplicado_interes == Decimal("30000.00")
    assert plan.resultado.aplicado_capital == Decimal("0.00")
    assert plan.actualizaciones[0].interes_pendiente == Decimal("0.00")
    assert plan.actualizaciones[0].capital_pendiente == Decimal("50000.00")
    assert plan.actualizaciones[1].capital_pendiente == Decimal("60000.00")
