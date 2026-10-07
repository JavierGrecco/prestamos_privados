from decimal import Decimal

import pytest

from dominio.distribucion_pago_v3 import (
    ParticipacionPagoV3,
    distribuir_pago_v3,
)
from dominio.excepciones import ErrorInvariante, ErrorValidacion


def p(i, pct):
    return ParticipacionPagoV3(i, Decimal(pct))


def test_50_50_conserva_centavos():
    r = distribuir_pago_v3(Decimal('30.00'), (p(1, '0.5'), p(2, '0.5')))
    assert [(x.inversor_id, x.monto) for x in r] == [(1, Decimal('15.00')), (2, Decimal('15.00'))]


def test_mayor_residuo_y_suma_exacta():
    r = distribuir_pago_v3(Decimal('100.00'), (p(1, '0.3333'), p(2, '0.3333'), p(3, '0.3334')))
    assert [(x.inversor_id, x.monto) for x in r] == [
        (1, Decimal('33.33')), (2, Decimal('33.33')), (3, Decimal('33.34'))
    ]
    assert sum((x.monto for x in r), Decimal('0')) == Decimal('100.00')


def test_residuo_empate_rompe_por_inversor_id():
    r = distribuir_pago_v3(Decimal('0.01'), (p(20, '0.5'), p(10, '0.5')))
    assert [(x.inversor_id, x.monto) for x in r] == [(20, Decimal('0.00')), (10, Decimal('0.01'))]


def test_porcentajes_no_suman_cien_es_error():
    with pytest.raises(ErrorInvariante, match='100%'):
        distribuir_pago_v3(Decimal('10'), (p(1, '0.4'), p(2, '0.5')))


def test_inversor_duplicado_es_error():
    with pytest.raises(ErrorInvariante, match='más de una vez'):
        distribuir_pago_v3(Decimal('10'), (p(1, '0.5'), p(1, '0.5')))


def test_monto_cero_es_error():
    with pytest.raises(ErrorValidacion, match='mayor a cero'):
        distribuir_pago_v3(Decimal('0'), (p(1, '1.0'),))
