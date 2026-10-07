from datetime import date
from decimal import Decimal

import pytest

from dominio.excepciones import ErrorInvariante, ErrorValidacion
from dominio.motor_pagos_v3 import (
    AplicacionPago,
    Devengamiento,
    ObligacionAfectada,
    ExcedentePago,
    ObligacionSnapshot,
    OrigenImputacion,
    SaldoObligacion,
    TipoPlanPago,
    TratamientoExcedente,
    calcular_plan_pago,
    decidir_tratamiento_excedente,
)
from dominio.tipos import ConceptoImputacion


def obligacion(
    cuota_id: int,
    numero: int,
    estado: str = "PENDIENTE",
    interes: str = "20000",
    capital: str = "100000",
    mora: str = "0",
    parcial: bool = False,
) -> ObligacionSnapshot:
    return ObligacionSnapshot(
        cuota_id=cuota_id,
        numero_cuota=numero,
        vencimiento=date(2026, 9, numero),
        estado=estado,
        tuvo_pago_parcial=parcial,
        saldo=SaldoObligacion(
            interes=Decimal(interes), capital=Decimal(capital), mora=Decimal(mora)
        ),
    )


def test_pago_parcial_aplica_interes_y_luego_capital():
    plan = calcular_plan_pago(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 10),
        revision_prestamo=1,
        monto_recibido=Decimal("50000"),
        obligaciones=(obligacion(1, 1),),
    )

    assert plan.aplicado_interes == Decimal("20000.00")
    assert plan.monto_a_capital == Decimal("30000.00")
    assert plan.excedente.monto == Decimal("0.00")
    assert plan.tipo is TipoPlanPago.PARCIAL
    afectada = plan.obligaciones_afectadas[0]
    assert afectada.saldo_posterior.interes == Decimal("0.00")
    assert afectada.saldo_posterior.capital == Decimal("70000.00")
    assert afectada.estado_posterior == "PARCIAL"
    assert afectada.tuvo_pago_parcial_posterior is True


def test_complemento_cierra_parcial_y_pasa_a_siguiente_cuota():
    plan = calcular_plan_pago(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 20),
        revision_prestamo=2,
        monto_recibido=Decimal("80000"),
        obligaciones=(
            obligacion(1, 1, estado="PARCIAL", interes="0", capital="70000", parcial=True),
            obligacion(2, 2, interes="25000", capital="90000"),
        ),
    )

    assert plan.excedente.monto == Decimal("0.00")
    assert plan.obligaciones_afectadas[0].estado_posterior == "PAGADA"
    assert plan.obligaciones_afectadas[0].aplicado_capital == Decimal("70000.00")
    assert plan.obligaciones_afectadas[1].aplicado_interes == Decimal("10000.00")
    assert plan.obligaciones_afectadas[1].saldo_posterior.interes == Decimal("15000.00")
    assert plan.tipo is TipoPlanPago.COMPLEMENTO

    # Trazabilidad multi-cuota: cada aplicación conserva su cuota real.
    assert tuple((a.cuota_id, a.concepto.value, a.monto) for a in plan.aplicaciones) == (
        (1, "CAPITAL", Decimal("70000.00")),
        (2, "INTERES", Decimal("10000.00")),
    )


def test_mora_se_aplica_antes_del_interes_y_capital():
    plan = calcular_plan_pago(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 30),
        revision_prestamo=1,
        monto_recibido=Decimal("25000"),
        obligaciones=(obligacion(1, 1, mora="5000", interes="12000", capital="30000"),),
    )

    assert plan.aplicado_mora == Decimal("5000.00")
    assert plan.aplicado_interes == Decimal("12000.00")
    assert plan.monto_a_capital == Decimal("8000.00")
    assert plan.monto_aplicado == Decimal("25000.00")


def test_interes_insuficiente_no_reduce_capital():
    plan = calcular_plan_pago(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 30),
        revision_prestamo=1,
        monto_recibido=Decimal("5000"),
        obligaciones=(obligacion(1, 1, interes="12000", capital="30000"),),
    )

    afectada = plan.obligaciones_afectadas[0]
    assert plan.aplicado_interes == Decimal("5000.00")
    assert plan.monto_a_capital == Decimal("0.00")
    assert afectada.saldo_posterior.interes == Decimal("7000.00")
    assert afectada.saldo_posterior.capital == Decimal("30000.00")


def test_devengamiento_mora_queda_identificado_por_origen_y_referencia():
    dev = Devengamiento(
        concepto=ConceptoImputacion.MORA,
        monto=Decimal("500.00"),
        fecha_desde=date(2026, 9, 10),
        fecha_hasta=date(2026, 9, 20),
        origen="MORA_CONTRACTUAL",
        referencia="mora-1",
    )
    plan = calcular_plan_pago(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 20),
        revision_prestamo=1,
        monto_recibido=Decimal("500"),
        obligaciones=(obligacion(1, 1, interes="0", capital="30000"),),
        devengamientos_por_cuota={1: (dev,)},
    )

    app = plan.aplicaciones[0]
    assert app.origen is OrigenImputacion.DEVENGAMIENTO
    assert app.referencias_devengamiento == ("mora-1",)
    assert plan.mora_generada == Decimal("500.00")


def test_excedente_no_tiene_tratamiento_automatico():
    plan = calcular_plan_pago(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 10),
        revision_prestamo=1,
        monto_recibido=Decimal("150000"),
        obligaciones=(obligacion(1, 1, interes="20000", capital="100000"),),
    )

    assert plan.excedente == ExcedentePago(Decimal("30000.00"))
    assert plan.tipo is TipoPlanPago.ADELANTO

    decidido = decidir_tratamiento_excedente(plan, TratamientoExcedente.PREPAGO_RAI)
    assert decidido.monto == Decimal("30000.00")
    assert decidido.tratamiento is TratamientoExcedente.PREPAGO_RAI
    assert plan.excedente.tratamiento is None


def test_plan_es_determinista_y_no_muta_los_snapshots():
    snapshot = obligacion(1, 1)
    original = snapshot

    plan_1 = calcular_plan_pago(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 10),
        revision_prestamo=1,
        monto_recibido=Decimal("50000"),
        obligaciones=(snapshot,),
    )
    plan_2 = calcular_plan_pago(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 10),
        revision_prestamo=1,
        monto_recibido=Decimal("50000"),
        obligaciones=(snapshot,),
    )

    assert plan_1 == plan_2
    assert snapshot == original


def test_no_permite_aplicacion_cero():
    with pytest.raises(ErrorValidacion):
        AplicacionPago(
            cuota_id=1,
            concepto=ConceptoImputacion.CAPITAL,
            monto=Decimal("0"),
            origen=OrigenImputacion.SALDO_CONTRACTUAL,
        )


def test_invariante_detecta_aplicacion_superior_al_saldo():
    afectada = ObligacionAfectada(
        cuota_id=1,
        numero_cuota=1,
        vencimiento=date(2026, 9, 1),
        estado_anterior="PENDIENTE",
        estado_posterior="PAGADA",
        saldo_anterior=SaldoObligacion(capital=Decimal("100")),
        devengamientos=(),
        aplicaciones=(
            AplicacionPago(
                cuota_id=1,
                concepto=ConceptoImputacion.CAPITAL,
                monto=Decimal("110"),
                origen=OrigenImputacion.SALDO_CONTRACTUAL,
            ),
        ),
        saldo_posterior=SaldoObligacion(),
        tuvo_pago_parcial_posterior=False,
    )
    with pytest.raises(ErrorInvariante):
        afectada.validar()


def test_rechaza_obligaciones_fuera_de_orden_cronologico():
    with pytest.raises(ErrorValidacion):
        calcular_plan_pago(
            prestamo_id=10,
            fecha_valor=date(2026, 9, 30),
            revision_prestamo=1,
            monto_recibido=Decimal("100"),
            obligaciones=(obligacion(2, 2), obligacion(1, 1)),
        )


def test_concepto_mixto_no_miente_sobre_el_origen():
    dev = Devengamiento(
        concepto=ConceptoImputacion.INTERES,
        monto=Decimal("500"),
        fecha_desde=date(2026, 9, 10),
        fecha_hasta=date(2026, 9, 20),
        origen="INTERES_ADICIONAL",
        referencia="int-1",
    )
    plan = calcular_plan_pago(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 20),
        revision_prestamo=1,
        monto_recibido=Decimal("1000"),
        obligaciones=(obligacion(1, 1, interes="800", capital="30000"),),
        devengamientos_por_cuota={1: (dev,)},
    )
    app = plan.aplicaciones[0]
    assert app.concepto is ConceptoImputacion.INTERES
    assert app.origen is OrigenImputacion.MIXTA
    assert app.referencias_devengamiento == ("int-1",)
    assert app.monto == Decimal("1000.00")


def test_conservacion_de_dinero_para_muchos_montos():
    obligacion_base = obligacion(1, 1, interes="25000", capital="75000")
    for centavos in range(1, 150001, 1379):
        monto = Decimal(centavos) / Decimal("100")
        plan = calcular_plan_pago(
            prestamo_id=10,
            fecha_valor=date(2026, 9, 20),
            revision_prestamo=1,
            monto_recibido=monto,
            obligaciones=(obligacion_base,),
        )
        assert plan.monto_aplicado + plan.excedente.monto == monto.quantize(Decimal("0.01"))
        assert all(
            valor >= Decimal("0.00")
            for afectada in plan.obligaciones_afectadas
            for valor in (
                afectada.saldo_posterior.mora,
                afectada.saldo_posterior.interes,
                afectada.saldo_posterior.capital,
            )
        )


def test_rechaza_politica_que_omite_un_concepto_con_saldo():
    with pytest.raises(ErrorValidacion):
        calcular_plan_pago(
            prestamo_id=10,
            fecha_valor=date(2026, 9, 20),
            revision_prestamo=1,
            monto_recibido=Decimal("100"),
            obligaciones=(obligacion(1, 1, interes="100", capital="100"),),
            orden_waterfall=(ConceptoImputacion.CAPITAL,),
        )


def test_waterfall_admite_politica_contrato_de_cinco_conceptos():
    from dominio.tipos import ConceptoImputacion as C

    plan = calcular_plan_pago(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 20),
        revision_prestamo=1,
        monto_recibido=Decimal("200"),
        obligaciones=(
            ObligacionSnapshot(
                cuota_id=1,
                numero_cuota=1,
                vencimiento=date(2026, 9, 1),
                estado="PENDIENTE",
                tuvo_pago_parcial=False,
                saldo=SaldoObligacion(gasto=Decimal("100"), mora=Decimal("100")),
            ),
        ),
        orden_waterfall=(C.GASTO, C.PENALIZACION, C.MORA, C.INTERES, C.CAPITAL),
    )

    assert plan.aplicaciones[0].concepto is C.GASTO
    assert plan.aplicaciones[1].concepto is C.MORA
    assert plan.excedente.monto == Decimal("0.00")
    assert plan.obligaciones_afectadas[0].estado_posterior == "PAGADA"
