"""
Tests del motor de amortización.

Verifican que:
  - Las cuotas conocidas coinciden con el cálculo manual.
  - El saldo final siempre es exactamente cero.
  - La suma de las amortizaciones reconstruye el capital.
  - Los plazos impares funcionan.
"""
from datetime import date
from decimal import Decimal

import pytest

from dominio import (
    generar_tabla, cuota_francesa,
    SistemaAmortizacion, ModalidadTasa,
)


class TestCuotaFrancesa:
    def test_cuota_conocida(self):
        """$20M a 30% TNA en 36 meses ≈ $849.030"""
        cuota = cuota_francesa(
            capital=Decimal("20000000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            meses=36,
        )
        assert cuota == pytest.approx(Decimal("849030"), abs=Decimal("2"))

    def test_tasa_cero(self):
        """Sin interés, la cuota es capital / meses."""
        cuota = cuota_francesa(
            capital=Decimal("1200000"),
            tasa_anual=Decimal("0"),
            modalidad=ModalidadTasa.TNA,
            meses=12,
        )
        assert cuota == Decimal("100000.00")


class TestTablaFrancesa:
    def test_cierra_en_cero(self):
        tabla = generar_tabla(
            capital=Decimal("1000000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            meses=12,
            fecha_inicio=date(2026, 1, 1),
            sistema=SistemaAmortizacion.FRANCES,
        )
        assert tabla[-1]["saldo"] == Decimal("0.00")

    def test_suma_capital_es_capital_original(self):
        """La suma de las amortizaciones debe ser el capital."""
        tabla = generar_tabla(
            capital=Decimal("1000000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            meses=12,
            fecha_inicio=date(2026, 1, 1),
            sistema=SistemaAmortizacion.FRANCES,
        )
        total = sum(f["capital"] for f in tabla)
        assert total == Decimal("1000000.00")

    def test_plazos_impares(self):
        """El motor acepta cualquier cantidad de meses."""
        for m in [6, 8, 13, 30, 47, 73]:
            tabla = generar_tabla(
                capital=Decimal("5000000"),
                tasa_anual=Decimal("0.30"),
                modalidad=ModalidadTasa.TNA,
                meses=m,
                fecha_inicio=date(2026, 1, 1),
                sistema=SistemaAmortizacion.FRANCES,
            )
            assert len(tabla) == m
            assert tabla[-1]["saldo"] == Decimal("0.00")


class TestTablaAlemana:
    def test_amortizacion_constante(self):
        tabla = generar_tabla(
            capital=Decimal("1200000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            meses=12,
            fecha_inicio=date(2026, 1, 1),
            sistema=SistemaAmortizacion.ALEMAN,
        )
        amortizaciones = [f["capital"] for f in tabla[:-1]]
        assert len(set(amortizaciones)) == 1
        assert tabla[-1]["saldo"] == Decimal("0.00")


class TestInteresOnly:
    def test_periodo_de_gracia(self):
        tabla = generar_tabla(
            capital=Decimal("1000000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            meses=18,
            fecha_inicio=date(2026, 1, 1),
            sistema=SistemaAmortizacion.INTERES_ONLY,
            meses_interes_only=6,
        )
        for f in tabla[:6]:
            assert f["capital"] == Decimal("0.00")
        assert tabla[5]["saldo"] == Decimal("1000000.00")
        assert tabla[-1]["saldo"] == Decimal("0.00")