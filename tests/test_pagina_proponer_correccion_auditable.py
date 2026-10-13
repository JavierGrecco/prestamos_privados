"""Pruebas de los campos numéricos y comparaciones del formulario de correcciones."""

from decimal import Decimal

import pytest

from dominio.excepciones import ErrorValidacion
from ui.pagina_proponer_correccion_auditable import (
    _formatear_decimal,
    _parsear_decimal,
    _snapshots_equivalentes,
)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("1.234,56", Decimal("1234.56")),
        ("1234,56", Decimal("1234.56")),
        ("1234.56", Decimal("1234.56")),
        ("1,234.56", Decimal("1234.56")),
        ("1.000,000000", Decimal("1000.000000")),
    ],
)
def test_parsea_importes_localizados_sin_float(texto, esperado):
    escala = Decimal("0.000001") if esperado.as_tuple().exponent == -6 else Decimal("0.01")
    assert _parsear_decimal(texto, campo="importe", escala=escala) == esperado


def test_formatea_decimal_en_notacion_local():
    assert _formatear_decimal(Decimal("1234567.8"), 2) == "1.234.567,80"
    assert _formatear_decimal(Decimal("1000"), 6) == "1.000,000000"


def test_rechaza_precision_excesiva_sin_redondear_silenciosamente():
    with pytest.raises(ErrorValidacion, match="como máximo 2 decimales"):
        _parsear_decimal(
            "1.234,567", campo="importe", escala=Decimal("0.01")
        )


@pytest.mark.parametrize("texto", ["0", "0,00", "-1,00", "NaN", "Infinity", ""])
def test_rechaza_cotizacion_cero_negativa_no_finita_o_vacia(texto):
    with pytest.raises(ErrorValidacion):
        _parsear_decimal(
            texto,
            campo="cotización",
            escala=Decimal("0.000001"),
        )


def test_comparacion_semantica_no_confunde_formatos_decimal_con_cambios():
    original = {
        "monto_ars": "1000.00",
        "cotizacion_ars_por_usd": "1000",
        "equivalente_usd": "1.00",
        "nota": "",
    }
    mismo_valor = {
        "monto_ars": "1000",
        "cotizacion_ars_por_usd": "1000.000000",
        "equivalente_usd": "1",
        "nota": "",
    }
    cambio_real = {**mismo_valor, "monto_ars": "1200.00"}

    assert _snapshots_equivalentes(original, mismo_valor)
    assert not _snapshots_equivalentes(original, cambio_real)
