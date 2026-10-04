"""Tests del cálculo de XIRR."""
from datetime import date
from decimal import Decimal

import pytest

from dominio import xirr


def test_xirr_simple():
    """Aporto 1000, cobro 1100 en 1 año → 10%."""
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
    assert r < Decimal("0")