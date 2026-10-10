"""Tests del cálculo de XIRR y de sus límites de seguridad."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from dominio import xirr
from dominio.excepciones import ErrorValidacion


def test_xirr_simple():
    """Aporto 1000, cobro 1100 en 1 año → 10 %."""
    flujos = [
        (date(2026, 1, 1), Decimal("-1000")),
        (date(2027, 1, 1), Decimal("1100")),
    ]
    r = xirr(flujos)
    assert r == pytest.approx(Decimal("0.10"), abs=Decimal("0.005"))


def test_xirr_con_perdida():
    """Aporto 1000, cobro 900 en 1 año → rendimiento negativo."""
    flujos = [
        (date(2026, 1, 1), Decimal("-1000")),
        (date(2027, 1, 1), Decimal("900")),
    ]
    r = xirr(flujos)
    assert r == pytest.approx(Decimal("-0.10"), abs=Decimal("0.005"))


def test_xirr_agrega_flujos_de_la_misma_fecha():
    """Aportes y cobros de una misma fecha se compensan antes del cálculo."""
    fecha_inicio = date(2026, 1, 1)
    flujos = [
        (fecha_inicio, Decimal("-1000")),
        (fecha_inicio, Decimal("200")),
        (fecha_inicio + timedelta(days=365), Decimal("880")),
    ]
    assert xirr(flujos) == pytest.approx(
        Decimal("0.10"), abs=Decimal("0.005")
    )


def test_xirr_rechaza_series_con_mas_de_un_cambio_de_signo():
    """Esta serie admite dos raíces reales: 10 % y 20 %."""
    inicio = date(2026, 1, 1)
    flujos = [
        (inicio, Decimal("-100")),
        (inicio + timedelta(days=365), Decimal("230")),
        (inicio + timedelta(days=730), Decimal("-132")),
    ]
    with pytest.raises(ErrorValidacion, match="alternan de signo más de una vez"):
        xirr(flujos)


def test_xirr_resuelve_tasa_negativa_mayor_que_menos_cien_por_ciento():
    inicio = date(2026, 1, 1)
    flujos = [
        (inicio, Decimal("-1000")),
        (inicio + timedelta(days=365), Decimal("500")),
    ]
    assert xirr(flujos) == pytest.approx(
        Decimal("-0.50"), abs=Decimal("0.005")
    )


def test_xirr_rechaza_montos_no_finitos():
    flujos = [
        (date(2026, 1, 1), Decimal("-1000")),
        (date(2027, 1, 1), Decimal("NaN")),
    ]
    with pytest.raises(ErrorValidacion, match="Decimal finito"):
        xirr(flujos)
