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




def test_consulta_un_snapshot_guardado_desde_la_ui(
    tmp_path: Path,
    monkeypatch,
):
    from datetime import date
    from decimal import Decimal

    ruta = tmp_path / "snapshot-reposicion-consulta-ui.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        repo = PlanesReposicionRepo(db)
        snapshot_id = repo.guardar_snapshot(
            nombre="Autocrédito ya guardado",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date(2026, 10, 10),
            capital_original_ars=Decimal("12000000.00"),
            datos={
                "esquema_snapshot": 1,
                "tipo_plan": "REPOSICION_INTERNA",
                "supuestos": {"benchmark": "Cartera USD de prueba"},
                "resultado": {
                    "capital_inicial_usd": Decimal("12000.00"),
                    "brecha_valor_final_benchmark_usd": Decimal("-315.27"),
                    "cuotas": [
                        {
                            "numero": 1,
                            "fecha_vencimiento": "2026-11-10",
                            "importe_total_usd": Decimal("1050.00"),
                            "saldo_capital_usd": Decimal("11000.00"),
                            "cotizacion": {"ars_por_usd": Decimal("1500.00")},
                            "equivalente_ars": Decimal("1575000.00"),
                        }
                    ],
                },
                "sensibilidad": [],
            },
            creado_por="admin",
        )
    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta))

    at = AppTest.from_file(APP, default_timeout=20)
    iniciar_apptest_autenticado(at, ruta)
    at.button(key="nav_simular_carencia").click()
    at.run()
    at.radio(key="sim_carencia_unidad").set_value(
        "USD de referencia — solo análisis"
    )
    at.run()

    selector = at.selectbox(key="sim_usd_snapshot_consulta_id")
    assert any("Autocrédito ya guardado" in str(option) for option in selector.options)
    assert snapshot_id == 1

    assert not at.exception
    assert any("**Análisis:** Autocrédito ya guardado" in str(item.value) for item in at.markdown)
    assert any(
        "No abre un contrato editable ni registra desembolsos o pagos"
        in str(item.value)
        for item in at.info
    )



def test_registra_aporte_de_reposicion_desde_la_ui(
    tmp_path: Path,
    monkeypatch,
):
    from datetime import date
    from decimal import Decimal

    ruta = tmp_path / "aporte-reposicion-ui.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        repo = PlanesReposicionRepo(db)
        plan_id = repo.guardar_snapshot(
            nombre="Auto familiar",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date(2026, 10, 1),
            capital_original_ars=Decimal("12000000.00"),
            datos={
                "esquema_snapshot": 1,
                "tipo_plan": "REPOSICION_INTERNA",
                "supuestos": {"benchmark": "Cartera USD de prueba"},
                "resultado": {
                    "cuotas": [
                        {
                            "numero": 1,
                            "fecha_vencimiento": "2026-09-10",
                            "importe_total_usd": Decimal("1100.00"),
                            "saldo_capital_usd": Decimal("10000.00"),
                        }
                    ]
                },
                "sensibilidad": [],
            },
            creado_por="admin",
        )
    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta))

    at = AppTest.from_file(APP, default_timeout=20)
    iniciar_apptest_autenticado(at, ruta)
    at.button(key="nav_simular_carencia").click()
    at.run()
    at.radio(key="sim_carencia_unidad").set_value(
        "USD de referencia — solo análisis"
    )
    at.run()

    at.text_input(key=f"sim_usd_aporte_monto_{plan_id}").set_value("1500000,00")
    at.text_input(key=f"sim_usd_aporte_tc_{plan_id}").set_value("1500,00")
    at.text_input(key=f"sim_usd_aporte_fuente_{plan_id}").set_value(
        "Cotización registrada para la prueba"
    )
    # No ejecutar un rerun entre editar campos y enviar el formulario:
    # Streamlit entrega esos cambios agrupados al pulsar el botón de envío.
    submit = at.button(key=f"sim_usd_aporte_submit_{plan_id}")
    assert submit.label == "Registrar aporte"
    submit.click().run()
    assert not at.exception
    assert any(
        f"Aporte #" in str(item.value) for item in at.success
    ), [str(item.value) for item in at.error]

    with BaseDatos(ruta) as db:
        repo = PlanesReposicionRepo(db)
        aportes = repo.listar_aportes(plan_id)
        if len(aportes) != 1:
            filas = db.consultar(
                "SELECT id, plan_id, monto_ars, creado_por FROM aportes_reposicion"
            )
            raise AssertionError({
                "plan_esperado": plan_id,
                "aporte_id_en_session": at.session_state.get("sim_usd_ultimo_aporte"),
                "exitos_ui": [str(item.value) for item in at.success],
                "errores_ui": [str(item.value) for item in at.error],
                "aportes_en_db": [dict(fila) for fila in filas],
            })
        assert aportes[0].monto_ars == Decimal("1500000.00")
        assert aportes[0].cotizacion_ars_por_usd == Decimal("1500.00")
        assert aportes[0].equivalente_usd == Decimal("1000.00")
        assert repo.verificar_aporte(repo.obtener_aporte(aportes[0].id))
