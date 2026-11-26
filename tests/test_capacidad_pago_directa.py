"""Regresiones del cálculo directo de capacidad de pago."""

from decimal import Decimal

import pytest

from aplicacion.consultas.capacidad_pago_directa import (
    evaluar_capacidad_pago_directa,
)


def test_calcula_remanente_y_porcentaje_sobre_margen_declarado():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual=Decimal("250000"),
        cuota_nueva_mensual=Decimal("160000"),
        colchon_mensual=Decimal("20000"),
    )

    assert resultado.margen_libre_declarado == Decimal("250000.00")
    assert resultado.cuota_nueva_mensual == Decimal("160000.00")
    assert resultado.colchon_mensual == Decimal("20000.00")
    assert resultado.remanente_mensual == Decimal("70000.00")
    assert resultado.porcentaje_margen_comprometido == Decimal("64.00")


def test_el_margen_cero_o_negativo_se_conserva_y_no_calcula_porcentaje():
    cero = evaluar_capacidad_pago_directa(
        margen_libre_mensual=Decimal("0"),
        cuota_nueva_mensual=Decimal("10000"),
    )
    negativo = evaluar_capacidad_pago_directa(
        margen_libre_mensual=Decimal("-15000"),
        cuota_nueva_mensual=Decimal("10000"),
    )

    assert cero.remanente_mensual == Decimal("-10000.00")
    assert cero.porcentaje_margen_comprometido is None
    assert negativo.remanente_mensual == Decimal("-25000.00")
    assert negativo.porcentaje_margen_comprometido is None


def test_permita_cuota_mayor_que_margen_y_muestra_faltante():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual=Decimal("80000"),
        cuota_nueva_mensual=Decimal("100000"),
    )

    assert resultado.remanente_mensual == Decimal("-20000.00")
    assert resultado.porcentaje_margen_comprometido == Decimal("125.00")


@pytest.mark.parametrize("cuota", ["0", "-1", "NaN", "Infinity", "-Infinity"])
def test_rechaza_cuota_invalida(cuota):
    with pytest.raises(ValueError):
        evaluar_capacidad_pago_directa(
            margen_libre_mensual=Decimal("100000"),
            cuota_nueva_mensual=cuota,
        )


def test_rechaza_colchon_negativo():
    with pytest.raises(ValueError, match="colchón mensual"):
        evaluar_capacidad_pago_directa(
            margen_libre_mensual=Decimal("100000"),
            cuota_nueva_mensual=Decimal("20000"),
            colchon_mensual=Decimal("-1"),
        )


@pytest.mark.parametrize("margen", ["NaN", "Infinity", "-Infinity"])
def test_rechaza_margen_no_finito(margen):
    with pytest.raises(ValueError, match="margen libre"):
        evaluar_capacidad_pago_directa(
            margen_libre_mensual=margen,
            cuota_nueva_mensual=Decimal("20000"),
        )


def test_redondea_porcentaje_con_precision_explicita():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual=Decimal("3"),
        cuota_nueva_mensual=Decimal("1"),
    )

    assert resultado.porcentaje_margen_comprometido == Decimal("33.33")
