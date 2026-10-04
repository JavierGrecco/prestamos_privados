"""
Tests del motor de recálculo RAI y RNI.
"""
from datetime import date
from decimal import Decimal

import pytest

from dominio import ModalidadTasa
from dominio.recalculo import (
    recalcular_rai,
    recalcular_rni,
    calcular_impacto,
)


class TestRAI:
    def test_capital_completo_mismo_plazo(self):
        """RAI mantiene el plazo original."""
        tabla = recalcular_rai(
            capital_pendiente=Decimal("800000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            meses_restantes=10,
            fecha_ultimo_vencimiento=date(2027, 10, 4),
        )
        assert len(tabla) == 10
        assert tabla[-1]["saldo"] == Decimal("0.00")

    def test_cuota_baja_con_menos_capital(self):
        """A menor capital, menor cuota."""
        tabla_full = recalcular_rai(
            capital_pendiente=Decimal("1000000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            meses_restantes=10,
            fecha_ultimo_vencimiento=date(2027, 10, 4),
        )
        tabla_reduc = recalcular_rai(
            capital_pendiente=Decimal("800000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            meses_restantes=10,
            fecha_ultimo_vencimiento=date(2027, 10, 4),
        )
        assert tabla_reduc[0]["cuota"] < tabla_full[0]["cuota"]


class TestRNI:
    def test_mismo_monto_menos_cuotas(self):
        """
        RNI mantiene la cuota y baja la cantidad de meses.

        Con capital de $500.000 y cuota de $97.487,13, se necesitan
        menos de 10 cuotas para pagar todo.
        """
        tabla, n = recalcular_rni(
            capital_pendiente=Decimal("500000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            cuota_objetivo=Decimal("97487.13"),
            fecha_ultimo_vencimiento=date(2027, 10, 4),
        )
        assert tabla is not None
        assert n < 10  # Menos de las 10 cuotas originales
        assert tabla[-1]["saldo"] == Decimal("0.00")

    def test_cuota_no_alcanza_devuelve_none(self):
        """Si la cuota no cubre ni los intereses, devuelve None."""
        tabla, n = recalcular_rni(
            capital_pendiente=Decimal("1000000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            cuota_objetivo=Decimal("1000"),  # mucho menor que los intereses
            fecha_ultimo_vencimiento=date(2027, 10, 4),
        )
        assert tabla is None
        assert n is None


class TestImpacto:
    def test_rai_mantiene_plazo(self):
        """RAI mantiene el plazo, entonces no ahorra meses."""
        tabla_restante = recalcular_rai(
            capital_pendiente=Decimal("900000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            meses_restantes=10,
            fecha_ultimo_vencimiento=date(2027, 10, 4),
        )
        tabla_rai = recalcular_rai(
            capital_pendiente=Decimal("500000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            meses_restantes=10,
            fecha_ultimo_vencimiento=date(2027, 10, 4),
        )
        imp_rai = calcular_impacto(tabla_restante, tabla_rai)
        assert imp_rai["meses_ahorrados"] == 0

    def test_rni_ahorra_meses(self):
        """RNI reduce el plazo, entonces ahorra meses."""
        tabla_restante = recalcular_rai(
            capital_pendiente=Decimal("900000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            meses_restantes=10,
            fecha_ultimo_vencimiento=date(2027, 10, 4),
        )
        tabla_rni, _ = recalcular_rni(
            capital_pendiente=Decimal("500000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            cuota_objetivo=Decimal("97487.13"),
            fecha_ultimo_vencimiento=date(2027, 10, 4),
        )
        imp_rni = calcular_impacto(tabla_restante, tabla_rni)
        assert imp_rni["meses_ahorrados"] > 0

    def test_rni_ahorra_mas_intereses_que_rai(self):
        """
        Con el mismo capital pendiente, RNI ahorra más intereses
        que RAI porque amortiza más rápido.
        """
        tabla_restante = recalcular_rai(
            capital_pendiente=Decimal("900000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            meses_restantes=10,
            fecha_ultimo_vencimiento=date(2027, 10, 4),
        )

        tabla_rai = recalcular_rai(
            capital_pendiente=Decimal("500000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            meses_restantes=10,
            fecha_ultimo_vencimiento=date(2027, 10, 4),
        )

        tabla_rni, _ = recalcular_rni(
            capital_pendiente=Decimal("500000"),
            tasa_anual=Decimal("0.30"),
            modalidad=ModalidadTasa.TNA,
            cuota_objetivo=Decimal("97487.13"),
            fecha_ultimo_vencimiento=date(2027, 10, 4),
        )

        imp_rai = calcular_impacto(tabla_restante, tabla_rai)
        imp_rni = calcular_impacto(tabla_restante, tabla_rni)

        assert imp_rni["ahorro"] > imp_rai["ahorro"]