"""Regresiones de interés por fechas: convención temporal y TNA/TEA coherentes."""
from datetime import date
from decimal import Decimal, localcontext

import pytest

from dominio import (
    ConvencionDias,
    ErrorValidacion,
    ModalidadTasa,
    interes_periodo,
    money,
    rate,
)


def test_actual_365_tea_usa_factor_efectivo_y_no_formula_lineal_tna() -> None:
    saldo = Decimal("100000")
    tasa = Decimal("0.21")
    inicio, fin = date(2026, 1, 1), date(2026, 2, 1)

    resultado = interes_periodo(
        saldo, tasa, ModalidadTasa.TEA, ConvencionDias.ACTUAL_365, inicio, fin
    )

    with localcontext() as contexto:
        contexto.prec = 40
        fraccion = Decimal((fin - inicio).days) / Decimal("365")
        factor = contexto.power(Decimal("1.21"), fraccion) - Decimal("1")
    esperado = money(saldo * rate(factor))
    lineal_incorrecto = money(
        saldo * tasa * Decimal((fin - inicio).days) / Decimal("365")
    )

    assert resultado == esperado
    assert resultado != lineal_incorrecto


def test_30e_360_prorratea_el_intervalo_real_de_dias_ajustados() -> None:
    resultado = interes_periodo(
        Decimal("100000"),
        Decimal("0.36"),
        ModalidadTasa.TNA,
        ConvencionDias.TREINTA_360,
        date(2026, 1, 1),
        date(2026, 1, 16),
    )

    assert resultado == Decimal("1500.00")


def test_actual_actual_separa_los_tramos_de_anios_distintos() -> None:
    resultado = interes_periodo(
        Decimal("100000"),
        Decimal("0.366"),
        ModalidadTasa.TNA,
        ConvencionDias.ACTUAL_ACTUAL,
        date(2024, 12, 15),
        date(2025, 1, 15),
    )

    # 17 días se calculan sobre 366 (2024) y 14 sobre 365 (2025).
    assert resultado == Decimal("3103.84")


@pytest.mark.parametrize("convencion", list(ConvencionDias))
def test_fecha_final_igual_o_anterior_no_devenga_interes(convencion) -> None:
    args = (
        Decimal("100000"),
        Decimal("0.36"),
        ModalidadTasa.TNA,
        convencion,
        date(2026, 1, 15),
    )
    assert interes_periodo(*args, date(2026, 1, 15)) == Decimal("0.00")
    assert interes_periodo(*args, date(2026, 1, 14)) == Decimal("0.00")


def test_mensual_conserva_tasa_completa_para_periodo_positivo() -> None:
    resultado = interes_periodo(
        Decimal("100000"),
        Decimal("0.36"),
        ModalidadTasa.TNA,
        ConvencionDias.MENSUAL,
        date(2026, 1, 1),
        date(2026, 1, 15),
    )

    assert resultado == Decimal("3000.00")


@pytest.mark.parametrize(
    ("saldo", "tasa"),
    [
        (Decimal("NaN"), Decimal("0.30")),
        (Decimal("Infinity"), Decimal("0.30")),
        (Decimal("1000"), Decimal("NaN")),
        (Decimal("1000"), Decimal("Infinity")),
    ],
)
def test_interes_rechaza_importes_y_tasas_no_finitos(saldo, tasa) -> None:
    with pytest.raises(ErrorValidacion, match="finito"):
        interes_periodo(
            saldo,
            tasa,
            ModalidadTasa.TNA,
            ConvencionDias.ACTUAL_365,
            date(2026, 1, 1),
            date(2026, 2, 1),
        )


def test_interes_rechaza_saldo_y_tasa_negativos() -> None:
    with pytest.raises(ErrorValidacion, match="saldo negativo"):
        interes_periodo(
            Decimal("-1.00"),
            Decimal("0.30"),
            ModalidadTasa.TNA,
            ConvencionDias.ACTUAL_365,
            date(2026, 1, 1),
            date(2026, 2, 1),
        )
    with pytest.raises(ErrorValidacion, match="no puede ser negativa"):
        interes_periodo(
            Decimal("1000"),
            Decimal("-0.30"),
            ModalidadTasa.TNA,
            ConvencionDias.ACTUAL_365,
            date(2026, 1, 1),
            date(2026, 2, 1),
        )
