"""Aceptación E2E del guardado y consulta de análisis de reposición USD."""

from pathlib import Path

import pytest

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
    descargas = {item.label for item in at.download_button}
    assert {"Descargar Markdown", "Descargar JSON", "Descargar CSV"} <= descargas



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



def test_registra_flujo_y_valuacion_de_inversion_desde_ui(
    tmp_path: Path,
    monkeypatch,
):
    from datetime import date, timedelta
    from decimal import Decimal

    ruta = tmp_path / "inversion-reposicion-ui.db"
    fecha_inicio = date.today() - timedelta(days=400)
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        repo = PlanesReposicionRepo(db)
        plan_id = repo.guardar_snapshot(
            nombre="Cartera real declarada",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=fecha_inicio,
            capital_original_ars=Decimal("12000000.00"),
            datos={
                "esquema_snapshot": 1,
                "tipo_plan": "REPOSICION_INTERNA",
                "supuestos": {"benchmark": "No verificado"},
                "resultado": {"cuotas": []},
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

    # Los selectores de moneda están fuera de cada formulario; cambiarlos
    # genera el rerun necesario para mostrar los campos correspondientes.
    at.radio(key=f"sim_usd_flujo_moneda_{plan_id}").set_value("USD")
    at.run()
    at.date_input(key=f"sim_usd_flujo_fecha_{plan_id}").set_value(
        date.today() - timedelta(days=365)
    )
    at.text_input(key=f"sim_usd_flujo_monto_{plan_id}").set_value("1000,00")
    at.button(key=f"sim_usd_flujo_submit_{plan_id}").click().run()
    assert not at.exception
    assert any("Movimiento de inversión" in str(item.value) for item in at.success)

    # Abrir una sesión de UI limpia para el segundo formulario evita conservar
    # widgets del rerun posterior al envío del primer formulario.
    at_val = AppTest.from_file(APP, default_timeout=20)
    iniciar_apptest_autenticado(at_val, ruta)
    at_val.button(key="nav_simular_carencia").click()
    at_val.run()
    at_val.radio(key="sim_carencia_unidad").set_value(
        "USD de referencia — solo análisis"
    )
    at_val.run()
    at_val.radio(key=f"sim_usd_valoracion_moneda_{plan_id}").set_value("USD")
    at_val.run()
    assert not at_val.exception
    at_val.date_input(key=f"sim_usd_valoracion_fecha_{plan_id}").set_value(date.today())
    at_val.text_input(key=f"sim_usd_valoracion_valor_{plan_id}").set_value("1100,00")
    assert any(
        button.key == f"sim_usd_valoracion_submit_{plan_id}"
        for button in at_val.button
    )
    at_val.button(key=f"sim_usd_valoracion_submit_{plan_id}").click().run()
    assert not at_val.exception
    assert any("Valuación de inversión" in str(item.value) for item in at_val.success)

    with BaseDatos(ruta) as db:
        repo = PlanesReposicionRepo(db)
        flujos = repo.listar_flujos_inversion(plan_id)
        valuaciones = repo.listar_valuaciones_inversion(plan_id)
        assert len(flujos) == 1
        assert len(valuaciones) == 1
        assert flujos[0].equivalente_usd == Decimal("1000.00")
        assert valuaciones[0].equivalente_usd == Decimal("1100.00")
        resumen = repo.resumen_rendimiento_inversion(plan_id)
        assert resumen.resultado_total_usd_ref == Decimal("100.00")
        assert resumen.xirr_anual == pytest.approx(Decimal("0.10"), abs=Decimal("0.005"))



def test_registra_flujo_y_valuacion_de_inversion_desde_ui(
    tmp_path: Path,
    monkeypatch,
):
    from datetime import date, timedelta
    from decimal import Decimal

    ruta = tmp_path / "inversion-reposicion-ui.db"
    fecha_inicio = date.today() - timedelta(days=400)
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        repo = PlanesReposicionRepo(db)
        plan_id = repo.guardar_snapshot(
            nombre="Cartera real declarada",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=fecha_inicio,
            capital_original_ars=Decimal("12000000.00"),
            datos={
                "esquema_snapshot": 1,
                "tipo_plan": "REPOSICION_INTERNA",
                "supuestos": {"benchmark": "No verificado"},
                "resultado": {"cuotas": []},
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

    # El selector está fuera del formulario; elegir USD muestra los campos apropiados.
    at.radio(key=f"sim_usd_flujo_moneda_{plan_id}").set_value("USD")
    at.run()
    at.date_input(key=f"sim_usd_flujo_fecha_{plan_id}").set_value(
        date.today() - timedelta(days=365)
    )
    at.text_input(key=f"sim_usd_flujo_monto_{plan_id}").set_value("1000,00")
    at.button(key=f"sim_usd_flujo_submit_{plan_id}").click().run()
    assert not at.exception
    assert any("Movimiento de inversión" in str(item.value) for item in at.success)

    at.radio(key=f"sim_usd_valoracion_moneda_{plan_id}").set_value("USD")
    at.run()
    at.date_input(key=f"sim_usd_valoracion_fecha_{plan_id}").set_value(date.today())
    at.text_input(key=f"sim_usd_valoracion_valor_{plan_id}").set_value("1100,00")
    at.button(key=f"sim_usd_valoracion_submit_{plan_id}").click().run()
    assert not at.exception
    assert any("Valuación de inversión" in str(item.value) for item in at.success)

    with BaseDatos(ruta) as db:
        repo = PlanesReposicionRepo(db)
        flujos = repo.listar_flujos_inversion(plan_id)
        valuaciones = repo.listar_valuaciones_inversion(plan_id)
        assert len(flujos) == 1
        assert len(valuaciones) == 1
        assert flujos[0].equivalente_usd == Decimal("1000.00")
        assert valuaciones[0].equivalente_usd == Decimal("1100.00")
        resumen = repo.resumen_rendimiento_inversion(plan_id)
        assert resumen.resultado_total_usd_ref == Decimal("100.00")
        assert resumen.xirr_anual == pytest.approx(Decimal("0.10"), abs=Decimal("0.005"))
