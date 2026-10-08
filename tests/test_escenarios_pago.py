"""Pruebas de las reglas puras para simular pagos."""
from decimal import Decimal

import pytest

from dominio.excepciones import ErrorValidacion
from dominio.tipos import ConceptoImputacion
from dominio.escenarios_pago import DeudaPago, simular_pago


class TestSimularPago:
    def test_pago_exactamente_igual_a_la_deuda(self):
        deuda = DeudaPago(
            cuota_interes=Decimal("300.00"),
            cuota_capital=Decimal("700.00"),
        )

        resultado = simular_pago(Decimal("1000.00"), deuda)

        assert resultado.tipo == "CUOTA"
        assert resultado.faltante == Decimal("0.00")
        assert resultado.excedente == Decimal("0.00")
        assert resultado.aplicado_interes == Decimal("300.00")
        assert resultado.aplicado_capital == Decimal("700.00")

    def test_pago_parcial_deja_faltante_y_calcula_costo_proyectado(self):
        deuda = DeudaPago(
            cuota_interes=Decimal("300.00"),
            cuota_capital=Decimal("700.00"),
        )

        resultado = simular_pago(
            Decimal("600.00"),
            deuda,
            tasa_mensual=Decimal("0.025"),
        )

        assert resultado.tipo == "PARCIAL"
        assert resultado.aplicado_interes == Decimal("300.00")
        assert resultado.aplicado_capital == Decimal("300.00")
        assert resultado.faltante == Decimal("400.00")
        assert resultado.capital_pendiente_despues == Decimal("400.00")
        assert resultado.interes_extra_estimado_proximo_periodo == Decimal("10.00")
        assert resultado.interes_extra_generado_por_pago == Decimal("10.00")

    def test_pago_mayor_a_la_deuda_es_adelanto(self):
        deuda = DeudaPago(
            cuota_interes=Decimal("300.00"),
            cuota_capital=Decimal("700.00"),
        )

        resultado = simular_pago(Decimal("1500.00"), deuda)

        assert resultado.tipo == "ADELANTO"
        assert resultado.faltante == Decimal("0.00")
        assert resultado.excedente == Decimal("500.00")
        assert resultado.aplicado_capital == Decimal("700.00")

    def test_la_mora_se_cobra_antes_que_el_interes(self):
        deuda = DeudaPago(
            cuota_interes=Decimal("300.00"),
            cuota_capital=Decimal("700.00"),
            mora_nueva=Decimal("100.00"),
        )

        resultado = simular_pago(Decimal("150.00"), deuda)

        assert resultado.aplicado_mora == Decimal("100.00")
        assert resultado.aplicado_interes == Decimal("50.00")
        assert resultado.aplicado_capital == Decimal("0.00")
        assert resultado.faltante == Decimal("950.00")

    def test_el_resultado_no_pierde_precision_decimal(self):
        deuda = DeudaPago(
            cuota_interes=Decimal("0.10"),
            cuota_capital=Decimal("0.20"),
        )

        resultado = simular_pago(Decimal("0.30"), deuda)

        assert resultado.total_deuda == Decimal("0.30")
        assert resultado.faltante == Decimal("0.00")
        assert resultado.aplicado_interes + resultado.aplicado_capital == Decimal("0.30")

    def test_rechaza_monto_no_positivo(self):
        deuda = DeudaPago(cuota_capital=Decimal("100.00"))

        with pytest.raises(ErrorValidacion):
            simular_pago(Decimal("0.00"), deuda)

    def test_separa_interes_total_proyectado_de_interes_generado_por_este_pago(self):
        deuda = DeudaPago(
            cuota_capital=Decimal("700.00"),
            arrastre_capital=Decimal("400.00"),
        )

        resultado = simular_pago(
            Decimal("300.00"),
            deuda,
            tasa_mensual=Decimal("0.025"),
        )

        # El pago no alcanza para cubrir el capital arrastrado y deja
        # pendiente toda la cuota actual. El próximo período se proyecta
        # sobre los $800 que quedan, pero el nuevo costo atribuible a esta
        # decisión corresponde solamente a los $700 de la cuota actual.
        assert resultado.capital_pendiente_despues == Decimal("800.00")
        assert resultado.interes_extra_estimado_proximo_periodo == Decimal("20.00")
        assert resultado.interes_extra_generado_por_pago == Decimal("17.50")

    def test_rechaza_deuda_negativa(self):
        with pytest.raises(ErrorValidacion):
            DeudaPago(cuota_capital=Decimal("-1.00"))

    def test_puede_cambiar_el_orden_de_imputacion_explicitamente(self):
        deuda = DeudaPago(
            cuota_interes=Decimal("300.00"),
            cuota_capital=Decimal("700.00"),
        )

        resultado = simular_pago(
            Decimal("100.00"),
            deuda,
            orden_imputacion=(
                ConceptoImputacion.CAPITAL,
                ConceptoImputacion.INTERES,
            ),
        )

        assert resultado.aplicado_capital == Decimal("100.00")
        assert resultado.aplicado_interes == Decimal("0.00")
