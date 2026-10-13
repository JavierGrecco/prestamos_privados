"""Contrato público del resumen utilizado por la pantalla de registro de pagos."""

from types import SimpleNamespace

from aplicacion.consultas.deuda_proximo_pago import (
    ResumenPrestamoParaPago,
    ServicioDeudaProximoPago,
)
from aplicacion.consultas.preview_pago import ServicioPreviewPago


def test_consulta_devuelve_un_resumen_publico_y_no_el_modelo_de_persistencia():
    modelo_persistido = SimpleNamespace(
        id=17,
        numero="PR-000017",
        destino="Autocrédito familiar",
        capital_original="100000.00",
    )

    class RepositorioPrestamosFalso:
        def obtener(self, prestamo_id):
            assert prestamo_id == 17
            return modelo_persistido

    consulta = ServicioDeudaProximoPago.__new__(ServicioDeudaProximoPago)
    consulta.prestamos = RepositorioPrestamosFalso()

    resultado = consulta.obtener_resumen_prestamo(17)

    assert resultado == ResumenPrestamoParaPago(
        prestamo_id=17,
        numero="PR-000017",
        destino="Autocrédito familiar",
    )
    assert resultado is not modelo_persistido
    assert not hasattr(resultado, "capital_original")


def test_consulta_devuelve_none_si_el_prestamo_no_existe():
    class RepositorioPrestamosFalso:
        @staticmethod
        def obtener(prestamo_id):
            return None

    consulta = ServicioDeudaProximoPago.__new__(ServicioDeudaProximoPago)
    consulta.prestamos = RepositorioPrestamosFalso()

    assert consulta.obtener_resumen_prestamo(999) is None


def test_fachada_publica_de_pago_delega_la_consulta_del_resumen():
    esperado = ResumenPrestamoParaPago(
        prestamo_id=4,
        numero="PR-000004",
        destino=None,
    )

    class ConsultaDeudaFalsa:
        @staticmethod
        def obtener_resumen_prestamo(prestamo_id):
            assert prestamo_id == 4
            return esperado

    servicio = ServicioPreviewPago.__new__(ServicioPreviewPago)
    servicio._deuda = ConsultaDeudaFalsa()

    assert servicio.obtener_resumen_prestamo(4) is esperado
