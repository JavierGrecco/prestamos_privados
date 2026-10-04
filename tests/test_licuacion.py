"""Tests del análisis de licuación."""
from decimal import Decimal

import pytest

from dominio import (
    factor_inflacion_acumulada, valor_real,
    proyectar_licuacion, calcular_tasa_real,
)


def test_factor_inflacion():
    """5% mensual durante 12 meses → 1.05^12 ≈ 1.796."""
    factor = factor_inflacion_acumulada(Decimal("0.05"), 12)
    assert factor == pytest.approx(Decimal("1.795856"), abs=Decimal("0.0001"))


def test_valor_real():
    """Una cuota de 850 mil con 5% mensual durante 12 meses
    vale en pesos de hoy aproximadamente 473 mil."""
    vr = valor_real(Decimal("850000"), Decimal("0.05"), 12)
    assert vr == pytest.approx(Decimal("473311"), abs=Decimal("500"))


def test_tasa_real_negativa():
    """Tasa 25%, inflación 30% → tasa real negativa."""
    r = calcular_tasa_real(Decimal("0.25"), Decimal("0.30"))
    assert r < Decimal("0")


def test_proyectar_licuacion():
    """A los 12 meses, la licuación debe ser significativa."""
    proyeccion = proyectar_licuacion(
        cuota_nominal=Decimal("850000"),
        inflacion_mensual=Decimal("0.05"),
        meses=12,
    )
    assert len(proyeccion) == 12
    # La licuación final debe ser positiva (perdiste poder de compra)
    assert proyeccion[-1]["licuacion_acumulada"] > Decimal("0.40")