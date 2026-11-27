"""Validación de valores Decimal en las primitivas financieras del dominio."""

from decimal import Decimal

import pytest

from dominio import ErrorValidacion, money, rate


VALORES_NO_FINITOS = [
    Decimal("NaN"),
    Decimal("sNaN"),
    Decimal("Infinity"),
    Decimal("-Infinity"),
    "NaN",
    "Infinity",
    "-Infinity",
    float("nan"),
    float("inf"),
    float("-inf"),
]


@pytest.mark.parametrize("normalizador", [money, rate], ids=["money", "rate"])
@pytest.mark.parametrize("valor", VALORES_NO_FINITOS)
def test_normalizadores_rechazan_valores_no_finitos(normalizador, valor):
    with pytest.raises(ErrorValidacion, match="finito"):
        normalizador(valor)


@pytest.mark.parametrize("normalizador", [money, rate], ids=["money", "rate"])
def test_normalizadores_rechazan_entradas_no_decimales(normalizador):
    with pytest.raises(ErrorValidacion, match="decimal válido"):
        normalizador("esto-no-es-un-numero")


def test_money_conserva_redondeo_comercial_a_centavos():
    assert money("100.555") == Decimal("100.56")
    assert money("-0.005") == Decimal("-0.01")
    assert money(100) == Decimal("100.00")


def test_rate_conserva_precision_de_ocho_decimales():
    assert rate("0.123456785") == Decimal("0.12345679")
    assert rate("0.025") == Decimal("0.02500000")


def test_normalizadores_rechazan_valores_fuera_del_contexto_decimal():
    with pytest.raises(ErrorValidacion, match="rango admitido"):
        money("1E+100")
    with pytest.raises(ErrorValidacion, match="rango admitido"):
        rate("1E+100")
