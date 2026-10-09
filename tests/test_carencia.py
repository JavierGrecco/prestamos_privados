"""Regresiones para el cálculo simple de intereses durante una carencia."""
from datetime import date
from decimal import Decimal

import pytest

from dominio import (
    ConvencionDias,
    ErrorValidacion,
    ModalidadTasa,
    calcular_interes_carencia_simple,
)


def _calcular(
    *,
    capital: str = "1000000",
    tasa: str = "0.36",
    modalidad: ModalidadTasa = ModalidadTasa.TNA,
    convencion: ConvencionDias = ConvencionDias.MENSUAL,
    inicio: date = date(2026, 1, 31),
    fin: date = date(2027, 1, 31),
):
    return calcular_interes_carencia_simple(
        capital=Decimal(capital),
        tasa_anual=Decimal(tasa),
        modalidad=modalidad,
        convencion=convencion,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )


def test_un_anio_mensual_al_36_por_ciento_devenga_interes_simple():
    resultado = _calcular()

    assert resultado.interes_total == Decimal("360000.00")
    assert len(resultado.tramos) == 12
    assert all(t.capital_base == Decimal("1000000") for t in resultado.tramos)
    assert all(t.interes == Decimal("30000.00") for t in resultado.tramos)


def test_carencia_de_cero_dias_no_devenga_interes():
    resultado = _calcular(inicio=date(2026, 4, 10), fin=date(2026, 4, 10))

    assert resultado.interes_total == Decimal("0.00")
    assert resultado.tramos == ()


def test_actual_365_utiliza_dias_reales_sin_interes_sobre_interes():
    resultado = _calcular(
        convencion=ConvencionDias.ACTUAL_365,
        inicio=date(2026, 1, 1),
        fin=date(2027, 1, 1),
    )

    assert abs(resultado.interes_total - Decimal("360000.00")) <= Decimal("0.10")
    assert all(t.capital_base == Decimal("1000000") for t in resultado.tramos)


def test_actual_actual_separa_el_cambio_de_anio():
    resultado = _calcular(
        convencion=ConvencionDias.ACTUAL_ACTUAL,
        inicio=date(2024, 1, 1),
        fin=date(2025, 1, 1),
    )

    assert resultado.interes_total == Decimal("360000.00")
    assert len(resultado.tramos) == 12
    assert all(t.capital_base == Decimal("1000000") for t in resultado.tramos)


def test_fecha_final_anterior_a_inicio_es_rechazada():
    with pytest.raises(ErrorValidacion, match="no puede preceder"):
        _calcular(inicio=date(2026, 2, 1), fin=date(2026, 1, 31))


@pytest.mark.parametrize(
    ("capital", "tasa"),
    [
        ("0", "0.36"),
        ("-1", "0.36"),
        ("1000000", "-0.01"),
    ],
)
def test_capital_o_tasa_invalidos_son_rechazados(capital: str, tasa: str):
    with pytest.raises(ErrorValidacion):
        _calcular(capital=capital, tasa=tasa)


def test_tasa_efectiva_anual_se_usa_con_la_modalidad_declarada():
    resultado = _calcular(
        tasa="0.30",
        modalidad=ModalidadTasa.TEA,
        inicio=date(2026, 1, 1),
        fin=date(2027, 1, 1),
    )

    assert resultado.interes_total > Decimal("300000.00")
    assert len(resultado.tramos) == 12
