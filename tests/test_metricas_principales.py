"""Pruebas unitarias del cálculo de métricas principales."""
from decimal import Decimal

from aplicacion.consultas.metricas_principales import (
    DatosMetricasPrincipales,
    calcular_metricas_principales,
)
from aplicacion.servicios.metricas_principales import ServicioMetricasPrincipales


def test_sin_datos_financieros_devuelve_resultado_estable():
    resultado = calcular_metricas_principales(
        DatosMetricasPrincipales(
            capital_invertido=Decimal("0"),
            capital_adeudado=Decimal("0"),
        )
    )

    assert resultado.capital_invertido == Decimal("0")
    assert resultado.capital_adeudado == Decimal("0")
    assert resultado.efecto_inversion == Decimal("0")
    assert resultado.efecto_deuda == Decimal("0")
    assert resultado.efecto_neto == Decimal("0")
    assert resultado.veredicto == "estable"
    assert resultado.detalle_inversion == "Todavía no tenés inversiones activas."
    assert resultado.detalle_deuda == "Todavía no tenés deudas activas."


def test_tna_equivalente_a_la_inflacion_no_genera_efecto_real():
    resultado = calcular_metricas_principales(
        DatosMetricasPrincipales(
            capital_invertido=Decimal("25000"),
            capital_adeudado=Decimal("100000"),
            tasa_anual=Decimal("0.60"),
            modalidad_tasa="TNA",
        ),
        inflacion_mensual=Decimal("0.05"),
    )

    assert resultado.efecto_inversion == Decimal("0")
    assert resultado.efecto_deuda == Decimal("0")
    assert resultado.efecto_neto == Decimal("0")
    assert resultado.veredicto == "estable"


def test_la_deuda_con_tasa_menor_a_inflacion_muestra_efecto_positivo():
    resultado = calcular_metricas_principales(
        DatosMetricasPrincipales(
            capital_invertido=Decimal("0"),
            capital_adeudado=Decimal("1000000"),
            tasa_anual=Decimal("0.12"),
            modalidad_tasa="TNA",
        ),
        inflacion_mensual=Decimal("0.05"),
    )

    assert resultado.efecto_deuda > Decimal("0")
    assert resultado.efecto_neto == resultado.efecto_deuda
    assert resultado.veredicto == "creciendo"
    assert resultado.detalle_deuda == "Se achica sola con la inflación"


def test_sin_tasa_disponible_no_inventa_un_efecto_deuda():
    resultado = calcular_metricas_principales(
        DatosMetricasPrincipales(
            capital_invertido=Decimal("0"),
            capital_adeudado=Decimal("100000"),
        )
    )

    assert resultado.efecto_deuda == Decimal("0")
    assert resultado.efecto_neto == Decimal("0")


class _FuenteDePrueba:
    def __init__(self, datos):
        self.datos = datos
        self.personas_consultadas = []

    def obtener(self, persona_id):
        self.personas_consultadas.append(persona_id)
        return self.datos


def test_servicio_usa_la_fuente_inyectada_y_el_calculo_compartido():
    datos = DatosMetricasPrincipales(
        capital_invertido=Decimal("1000"),
        capital_adeudado=Decimal("0"),
    )
    fuente = _FuenteDePrueba(datos)
    servicio = ServicioMetricasPrincipales(fuente)

    resultado = servicio.obtener(42)

    assert fuente.personas_consultadas == [42]
    assert resultado.capital_invertido == Decimal("1000")
    assert resultado.capital_adeudado == Decimal("0")
