from datetime import date
from decimal import Decimal

import pytest

from dominio.adelanto_v3 import CuotaFuturaAdelantoV3, planificar_adelanto_v3
from dominio.excepciones import ErrorInvariante, ErrorValidacion
from dominio.tipos import ModalidadTasa, SistemaAmortizacion, TipoRecalculo


def cuotas():
    return (
        CuotaFuturaAdelantoV3(10, 2, date(2027, 1, 1), Decimal('920'), Decimal('20'), Decimal('80'), Decimal('100'), Decimal('820')),
        CuotaFuturaAdelantoV3(11, 3, date(2027, 2, 1), Decimal('840'), Decimal('18'), Decimal('82'), Decimal('100'), Decimal('738')),
        CuotaFuturaAdelantoV3(12, 4, date(2027, 3, 1), Decimal('758'), Decimal('16'), Decimal('84'), Decimal('100'), Decimal('674')),
    )


def rai_stub(**kwargs):
    return [
        {'capital_inicial': '820', 'interes': '10', 'capital': '410', 'cuota': '420', 'saldo': '410', 'vencimiento': date(1900,1,1)},
        {'capital_inicial': '410', 'interes': '9', 'capital': '410', 'cuota': '419', 'saldo': '0', 'vencimiento': date(1900,2,1)},
        {'capital_inicial': '410', 'interes': '8', 'capital': '0', 'cuota': '8', 'saldo': '0', 'vencimiento': date(1900,3,1)},
    ]


def rni_stub(**kwargs):
    return ([
        {'capital_inicial': '820', 'interes': '10', 'capital': '410', 'cuota': '420', 'saldo': '410', 'vencimiento': date(1900,1,1)},
        {'capital_inicial': '410', 'interes': '9', 'capital': '410', 'cuota': '419', 'saldo': '0', 'vencimiento': date(1900,2,1)},
    ], 2)


def test_rai_conserva_cantidad_y_fechas():
    p = planificar_adelanto_v3(
        tipo=TipoRecalculo.RAI, cuotas_futuras=cuotas(), monto_adelanto=Decimal('100'),
        tasa_anual=Decimal('0.24'), modalidad_tasa=ModalidadTasa.TNA,
        sistema=SistemaAmortizacion.FRANCES, recalcular_rai_fn=rai_stub,
    )
    assert p.capital_antes == Decimal('920.00')
    assert p.capital_despues == Decimal('820.00')
    assert p.cuotas_despues == 3
    assert [x.vencimiento for x in p.cuotas_nuevas] == [date(2027,1,1),date(2027,2,1),date(2027,3,1)]
    assert p.intereses_ahorrados == Decimal('27.00')


def test_rni_acorta_plazo_y_conserva_primeras_fechas():
    p = planificar_adelanto_v3(
        tipo=TipoRecalculo.RNI, cuotas_futuras=cuotas(), monto_adelanto=Decimal('100'),
        tasa_anual=Decimal('0.24'), modalidad_tasa=ModalidadTasa.TNA,
        sistema=SistemaAmortizacion.FRANCES, recalcular_rni_fn=rni_stub,
    )
    assert p.cuotas_despues == 2
    assert [x.numero for x in p.cuotas_nuevas] == [2,3]
    assert [x.vencimiento for x in p.cuotas_nuevas] == [date(2027,1,1),date(2027,2,1)]


def test_adelanto_mayor_que_capital_es_error():
    with pytest.raises(ErrorValidacion, match='excede'):
        planificar_adelanto_v3(
            tipo=TipoRecalculo.RAI, cuotas_futuras=cuotas(), monto_adelanto=Decimal('921'),
            tasa_anual=Decimal('0.24'), modalidad_tasa=ModalidadTasa.TNA,
            recalcular_rai_fn=rai_stub,
        )


def test_capital_cero_elimina_solo_horizonte_futuro():
    p = planificar_adelanto_v3(
        tipo=TipoRecalculo.RAI, cuotas_futuras=cuotas(), monto_adelanto=Decimal('920'),
        tasa_anual=Decimal('0.24'), modalidad_tasa=ModalidadTasa.TNA,
        recalcular_rai_fn=rai_stub,
    )
    assert p.cuotas_despues == 0
    assert p.intereses_despues == Decimal('0.00')
    assert p.intereses_ahorrados == Decimal('54.00')


def test_adelanto_no_oculta_interes_futuro_mayor():
    def bad(**kwargs):
        return [
            {'capital_inicial':'820','interes':'60','capital':'820','cuota':'880','saldo':'0','vencimiento':date(1900,1,1)},
            {'capital_inicial':'0','interes':'0','capital':'0','cuota':'0','saldo':'0','vencimiento':date(1900,2,1)},
            {'capital_inicial':'0','interes':'0','capital':'0','cuota':'0','saldo':'0','vencimiento':date(1900,3,1)},
        ]
    with pytest.raises(ErrorInvariante, match='aumentar'):
        planificar_adelanto_v3(
            tipo=TipoRecalculo.RAI, cuotas_futuras=cuotas(), monto_adelanto=Decimal('100'),
            tasa_anual=Decimal('0.24'), modalidad_tasa=ModalidadTasa.TNA,
            recalcular_rai_fn=bad,
        )
