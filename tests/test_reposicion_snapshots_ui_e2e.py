"""Aceptación E2E del guardado y consulta de análisis de reposición USD."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PlanesReposicionRepo
from tests.ui_auth_helpers import iniciar_apptest_autenticado


APP = Path(__file__).resolve().parents[1] / "ui" / "app.py"


def test_guarda_y_vuelve_a_consultar_un_analisis_desde_la_ui(
    tmp_path: Path,
    monkeypatch,
):
    ruta = tmp_path / "snapshot-reposicion-ui.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta))

    at = AppTest.from_file(APP, default_timeout=20)
    iniciar_apptest_autenticado(at, ruta)
    at.button(key="nav_simular_carencia").click()
    at.run()
    assert not at.exception

    at.radio(key="sim_carencia_unidad").set_value(
        "USD de referencia — solo análisis"
    )
    at.run()
    assert not at.exception

    at.text_input(key="sim_usd_fuente_tc").set_value("Cotización de prueba")
    at.text_input(key="sim_usd_benchmark_inversion").set_value(
        "Cartera USD de prueba"
    )
    at.run()
    assert not at.exception

    at.text_input(key="sim_usd_nombre_snapshot").set_value("Autocrédito E2E")
    at.button(key="sim_usd_guardar_snapshot").click()
    at.run()
    assert not at.exception

    with BaseDatos(ruta) as db:
        repo = PlanesReposicionRepo(db)
        snapshots = repo.listar_resumenes()
        assert len(snapshots) == 1
        snapshot_id = snapshots[0].id
        guardado = repo.obtener_snapshot(snapshot_id)
        assert guardado is not None
        assert repo.verificar_snapshot(guardado)
        assert guardado.nombre == "Autocrédito E2E"
        assert guardado.tipo_plan == "REPOSICION_INTERNA"

    at.selectbox(key="sim_usd_snapshot_consulta_id").set_value(snapshot_id)
    at.run()
    assert not at.exception
    assert any("Autocrédito E2E" in str(item.value) for item in at.markdown)
    assert any(
        "No abre un contrato editable ni registra desembolsos o pagos"
        in str(item.value)
        for item in at.info
    )
