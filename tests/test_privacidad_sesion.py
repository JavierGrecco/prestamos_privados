"""Pruebas de aislamiento de datos financieros temporales entre sesiones."""

from decimal import Decimal

from ui.privacidad_sesion import limpiar_datos_financieros_temporales


def test_limpia_todos_los_datos_de_mi_espacio_y_conserva_el_contexto_ui():
    estado = {
        "mi_espacio_margen_libre": Decimal("125000.00"),
        "mi_espacio_reserva_liquida": Decimal("800000.00"),
        "mi_espacio_capacidad_resultado": object(),
        "mi_espacio_cobros_externos_7_2": [{"monto": "50000.00"}],
        "tema": "oscuro",
        "pagina": "mi_espacio",
        "persona_id": 7,
        "usuario_app_id": 2,
        "usuario_app_revision": 4,
    }

    cantidad = limpiar_datos_financieros_temporales(estado)

    assert cantidad == 4
    assert not any(
        clave.startswith("mi_espacio_")
        for clave in estado
    )
    assert estado == {
        "tema": "oscuro",
        "pagina": "mi_espacio",
        "persona_id": 7,
        "usuario_app_id": 2,
        "usuario_app_revision": 4,
    }


def test_limpiar_sesion_sin_datos_financieros_es_seguro_y_repetible():
    estado = {"tema": "oscuro", "usuario_app_id": 1}

    assert limpiar_datos_financieros_temporales(estado) == 0
    assert limpiar_datos_financieros_temporales(estado) == 0
    assert estado == {"tema": "oscuro", "usuario_app_id": 1}
