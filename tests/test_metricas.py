"""
Tests de las métricas de la pantalla principal.
"""
from decimal import Decimal

from ui.metricas import (
    formatear_pesos,
    formatear_pesos_con_signo,
    color_para_veredicto,
    emoji_para_veredicto,
    _veredicto,
)


class TestFormato:

    def test_formatear_pesos_positivo(self):
        assert formatear_pesos(Decimal("1234567.89")) == "$ 1.234.567,89"

    def test_formatear_pesos_negativo(self):
        assert formatear_pesos(Decimal("-1234567.89")) == "-$ 1.234.567,89"

    def test_formatear_pesos_cero(self):
        assert formatear_pesos(Decimal("0")) == "$ 0,00"

    def test_formatear_con_signo_positivo(self):
        assert formatear_pesos_con_signo(Decimal("500")) == "+ $ 500,00"

    def test_formatear_con_signo_negativo(self):
        assert formatear_pesos_con_signo(Decimal("-500")) == "- $ 500,00"

    def test_formatear_con_signo_cero(self):
        assert formatear_pesos_con_signo(Decimal("0")) == "$ 0,00"


class TestVeredicto:

    def test_positivo_grande(self):
        v, msg = _veredicto(Decimal("50000"))
        assert v == "creciendo"
        assert "creciendo" in msg

    def test_negativo_grande(self):
        v, msg = _veredicto(Decimal("-50000"))
        assert v == "achicandose"
        assert "achicando" in msg

    def test_cerca_de_cero(self):
        v, msg = _veredicto(Decimal("5000"))
        assert v == "estable"
        assert "estable" in msg


class TestColores:

    def test_color_creciendo(self):
        assert color_para_veredicto("creciendo") == "color-verde"

    def test_color_achicandose(self):
        assert color_para_veredicto("achicandose") == "color-rojo"

    def test_color_estable(self):
        assert color_para_veredicto("estable") == "color-neutro"

    def test_emoji_creciendo(self):
        assert emoji_para_veredicto("creciendo") == "🟢"

    def test_emoji_achicandose(self):
        assert emoji_para_veredicto("achicandose") == "🔴"