from datetime import date
from decimal import Decimal

from aplicacion.servicios.plan_pago_v3_devengamientos import calcular_plan_pago_con_devengamientos
from aplicacion.servicios.registro_pago_v3 import EstadoRegistroPagoV3
from dominio.devengamiento_v3 import PoliticaInteres
from dominio.motor_pagos_v3 import ObligacionSnapshot
from dominio.politica_devengamiento_v3 import PoliticaInteresCapitalPendiente, ORIGEN_INTERES_CAPITAL_PENDIENTE
from dominio.tipos import ConceptoImputacion, ConvencionDias, ModalidadTasa


def estado(*, capital=Decimal('1000'), interes=Decimal('0')):
    o=ObligacionSnapshot.desde_cuota_actual(
        cuota_id=1, numero_cuota=1, vencimiento=date(2026,11,1), estado='PARCIAL',
        tuvo_pago_parcial=True, interes_pendiente=interes,
        capital_pendiente=capital, mora_pendiente=Decimal('0')
    )
    return EstadoRegistroPagoV3(prestamo_id=1, revision_prestamo=3, obligaciones=(o,))


def politica():
    return PoliticaInteresCapitalPendiente(
        PoliticaInteres(Decimal('0.24'), ModalidadTasa.TNA, ConvencionDias.ACTUAL_365)
    )


def test_incorpora_devengamiento_al_plan_y_a_su_origen():
    r=calcular_plan_pago_con_devengamientos(
        estado=estado(), fecha_valor=date(2026,11,11), monto_recibido=Decimal('10'), politica_interes_capital=politica()
    )
    assert r.devengamientos_nuevos[1][0].monto == Decimal('6.58')
    assert len(r.plan.aplicaciones) == 2
    app=r.plan.aplicaciones[0]
    assert app.concepto is ConceptoImputacion.INTERES
    assert app.origen.value == 'DEVENGAMIENTO'
    assert app.referencias_devengamiento
    assert r.plan.monto_a_capital == Decimal('3.42')
    assert r.plan.aplicado_interes == Decimal('6.58')


def test_no_duplica_si_ya_hay_corte_hasta_la_fecha():
    r=calcular_plan_pago_con_devengamientos(
        estado=estado(), fecha_valor=date(2026,11,11), monto_recibido=Decimal('100'),
        politica_interes_capital=politica(), ultimo_hasta_por_cuota={1: date(2026,11,11)}
    )
    assert r.devengamientos_nuevos == {}
    assert r.plan.aplicaciones[0].concepto is ConceptoImputacion.CAPITAL


def test_usa_capital_actual_para_un_nuevo_periodo():
    r=calcular_plan_pago_con_devengamientos(
        estado=estado(capital=Decimal('500')), fecha_valor=date(2026,11,21), monto_recibido=Decimal('20'),
        politica_interes_capital=politica(), ultimo_hasta_por_cuota={1: date(2026,11,11)}
    )
    d=r.devengamientos_nuevos[1][0]
    assert d.base == Decimal('500.00')
    assert d.fecha_desde == date(2026,11,11)
    assert d.fecha_hasta == date(2026,11,21)
    assert r.plan.aplicado_interes == Decimal('3.29')


def test_no_agrega_interes_adicional_antes_del_vencimiento():
    r=calcular_plan_pago_con_devengamientos(
        estado=estado(), fecha_valor=date(2026,10,25), monto_recibido=Decimal('100'),
        politica_interes_capital=politica()
    )
    assert r.devengamientos_nuevos == {}
    assert r.plan.monto_a_capital == Decimal('100.00')


def test_el_evento_no_se_capitaliza_silenciosamente():
    r=calcular_plan_pago_con_devengamientos(
        estado=estado(), fecha_valor=date(2026,11,11), monto_recibido=Decimal('1'), politica_interes_capital=politica()
    )
    assert r.plan.monto_a_capital == Decimal('0.00')
    assert r.plan.aplicado_interes == Decimal('1.00')
    assert r.plan.aplicaciones[0].concepto is ConceptoImputacion.INTERES
