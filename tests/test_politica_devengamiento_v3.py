from datetime import date
from decimal import Decimal

import pytest

from dominio.devengamiento_v3 import PoliticaInteres
from dominio.excepciones import ErrorValidacion
from dominio.motor_pagos_v3 import ObligacionSnapshot
from dominio.politica_devengamiento_v3 import (
    ORIGEN_INTERES_CAPITAL_PENDIENTE,
    PoliticaInteresCapitalPendiente,
    generar_interes_capital_pendiente,
)
from dominio.tipos import ConvencionDias, ModalidadTasa


def politica():
    return PoliticaInteresCapitalPendiente(
        PoliticaInteres(Decimal('0.24'), ModalidadTasa.TNA, ConvencionDias.ACTUAL_365)
    )


def obligacion(venc=date(2026,11,1), capital=Decimal('1000')):
    return ObligacionSnapshot.desde_cuota_actual(
        cuota_id=1, numero_cuota=1, vencimiento=venc, estado='PARCIAL',
        tuvo_pago_parcial=True, interes_pendiente=Decimal('0'),
        capital_pendiente=capital, mora_pendiente=Decimal('0')
    )


def test_no_devenga_antes_o_en_vencimiento():
    assert generar_interes_capital_pendiente(obligaciones=(obligacion(),), fecha_valor=date(2026,11,1), politica=politica()) == {}
    assert generar_interes_capital_pendiente(obligaciones=(obligacion(),), fecha_valor=date(2026,10,31), politica=politica()) == {}


def test_devenga_desde_vencimiento_sobre_capital_actual():
    r=generar_interes_capital_pendiente(obligaciones=(obligacion(),), fecha_valor=date(2026,11,11), politica=politica())
    d=r[1][0]
    assert d.base == Decimal('1000.00')
    assert d.fecha_desde == date(2026,11,1)
    assert d.fecha_hasta == date(2026,11,11)
    assert d.monto == Decimal('6.58')
    assert d.origen == ORIGEN_INTERES_CAPITAL_PENDIENTE


def test_no_duplica_periodo_ya_devengado():
    r=generar_interes_capital_pendiente(
        obligaciones=(obligacion(),), fecha_valor=date(2026,11,11), politica=politica(),
        ultimo_hasta_por_cuota={1: date(2026,11,11)}
    )
    assert r == {}


def test_continua_desde_ultimo_corte():
    r=generar_interes_capital_pendiente(
        obligaciones=(obligacion(),), fecha_valor=date(2026,11,21), politica=politica(),
        ultimo_hasta_por_cuota={1: date(2026,11,11)}
    )
    d=r[1][0]
    assert d.fecha_desde == date(2026,11,11)
    assert d.fecha_hasta == date(2026,11,21)
    assert d.base == Decimal('1000.00')


def test_no_devenga_sin_capital():
    assert generar_interes_capital_pendiente(obligaciones=(obligacion(capital=Decimal('0')),), fecha_valor=date(2026,11,11), politica=politica()) == {}


def test_mensual_no_inventa_prorrata():
    p=PoliticaInteresCapitalPendiente(PoliticaInteres(Decimal('0.24'), ModalidadTasa.TNA, ConvencionDias.MENSUAL))
    with pytest.raises(ErrorValidacion, match='meses completos'):
        generar_interes_capital_pendiente(obligaciones=(obligacion(),), fecha_valor=date(2026,11,15), politica=p)


def test_determinista():
    a=generar_interes_capital_pendiente(obligaciones=(obligacion(),), fecha_valor=date(2026,11,11), politica=politica())
    b=generar_interes_capital_pendiente(obligaciones=(obligacion(),), fecha_valor=date(2026,11,11), politica=politica())
    assert a == b
