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

def test_evalua_reserva_liquida_para_varios_meses_ajustados():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual="250000",
        cuota_nueva_mensual="160000",
        colchon_mensual="20000",
        reserva_liquida_disponible="180000",
        reserva_minima_protegida="30000",
        margen_libre_mes_ajustado="100000",
        meses_escenario_ajustado=2,
    )

    respaldo = resultado.respaldo_liquidez
    assert resultado.remanente_mensual == Decimal("70000.00")
    assert respaldo.reserva_utilizable == Decimal("150000.00")
    assert respaldo.remanente_mes_ajustado == Decimal("-80000.00")
    assert respaldo.faltante_mensual_escenario == Decimal("80000.00")
    assert respaldo.respaldo_requerido_escenario == Decimal("160000.00")
    assert respaldo.meses_completos_cubiertos == 1
    assert respaldo.respaldo_consumido_escenario == Decimal("150000.00")
    assert respaldo.respaldo_restante_escenario == Decimal("0.00")
    assert respaldo.faltante_no_cubierto_escenario == Decimal("10000.00")


def test_reserva_protegida_no_se_utiliza_y_puede_cubrir_el_escenario():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual="200000",
        cuota_nueva_mensual="100000",
        reserva_liquida_disponible="200000",
        reserva_minima_protegida="150000",
        margen_libre_mes_ajustado="80000",
        meses_escenario_ajustado=2,
    )

    respaldo = resultado.respaldo_liquidez
    assert respaldo.reserva_utilizable == Decimal("50000.00")
    assert respaldo.respaldo_requerido_escenario == Decimal("40000.00")
    assert respaldo.meses_completos_cubiertos == 2
    assert respaldo.respaldo_restante_escenario == Decimal("10000.00")
    assert respaldo.faltante_no_cubierto_escenario == Decimal("0.00")


def test_no_consumir_reserva_si_el_margen_ajustado_alcanza():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual="200000",
        cuota_nueva_mensual="100000",
        reserva_liquida_disponible="50000",
        margen_libre_mes_ajustado="120000",
        meses_escenario_ajustado=3,
    )

    respaldo = resultado.respaldo_liquidez
    assert respaldo.remanente_mes_ajustado == Decimal("20000.00")
    assert respaldo.respaldo_requerido_escenario == Decimal("0.00")
    assert respaldo.respaldo_consumido_escenario == Decimal("0.00")
    assert respaldo.respaldo_restante_escenario == Decimal("50000.00")
    assert respaldo.meses_completos_cubiertos == 3


def test_no_informa_cobertura_de_reserva_sin_escenario_ajustado():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual="200000",
        cuota_nueva_mensual="100000",
        reserva_liquida_disponible="50000",
    )

    respaldo = resultado.respaldo_liquidez
    assert respaldo.reserva_utilizable == Decimal("50000.00")
    assert respaldo.margen_libre_mes_ajustado is None
    assert respaldo.meses_completos_cubiertos is None
    assert respaldo.respaldo_consumido_escenario is None


def test_rechaza_reserva_protegida_mayor_al_ahorro_disponible():
    with pytest.raises(ValueError, match="no puede superar"):
        evaluar_capacidad_pago_directa(
            margen_libre_mensual="100000",
            cuota_nueva_mensual="20000",
            reserva_liquida_disponible="50000",
            reserva_minima_protegida="60000",
        )


@pytest.mark.parametrize("meses", [0, -1, 25, True, 1.5])
def test_rechaza_duracion_invalida_del_escenario_ajustado(meses):
    with pytest.raises(ValueError, match="duración del escenario"):
        evaluar_capacidad_pago_directa(
            margen_libre_mensual="100000",
            cuota_nueva_mensual="20000",
            margen_libre_mes_ajustado="50000",
            meses_escenario_ajustado=meses,
        )


def test_rechaza_margen_no_finito_en_escenario_ajustado():
    with pytest.raises(ValueError, match="mes ajustado"):
        evaluar_capacidad_pago_directa(
            margen_libre_mensual="100000",
            cuota_nueva_mensual="20000",
            margen_libre_mes_ajustado="NaN",
        )

