"""Aceptación de las capacidades de ciclo de vida en la UI."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.test_ui_e2e import app_database


APP = Path(__file__).resolve().parents[1] / "ui" / "app.py"


def _run():
    at = AppTest.from_file(APP, default_timeout=10)
    at.run()
    assert not at.exception
    return at


def test_lista_expone_filtro_de_ciclo_de_vida(app_database):
    at = _run()
    at.segmented_control(key="pagina").set_value("prestamos")
    at.run()
    assert not at.exception

    assert at.segmented_control(key="prestamos_estado_filtro").value == "ACTIVOS"

    at.segmented_control(key="prestamos_estado_filtro").set_value("TODOS")
    at.run()
    assert not at.exception
    assert at.segmented_control(key="prestamos_estado_filtro").value == "TODOS"


def test_detalle_expone_transiciones_controladas(app_database):
    at = _run()
    at.segmented_control(key="pagina").set_value("prestamos")
    at.run()
    at.button(key="ver_prestamo_1").click()
    at.run()
    assert not at.exception

    valores = at.selectbox(key="estado_destino_1").options
    assert "EN_MORA" in valores
    assert "FINALIZADO" in valores
    assert "CANCELADO" in valores
    assert any("Ciclo de vida" in str(m.value) for m in at.markdown)
