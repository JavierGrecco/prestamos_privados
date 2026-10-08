"""Aceptación end-to-end de la aplicación Streamlit.

Ejecuta el entrypoint real sobre una base SQLite temporal y recorre las áreas
principales de la aplicación sin depender de la base local del desarrollador.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


APP = Path(__file__).resolve().parents[1] / "ui" / "app.py"


@pytest.fixture
def app_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ruta = tmp_path / "ui.db"

    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)

        deudor_id = personas.crear(
            nombre="Javier",
            apellido="Prueba",
            documento="99990001",
        )
        personas.agregar_rol(deudor_id, "DEUDOR")
        personas.agregar_rol(deudor_id, "INVERSOR")

        inversor_id = personas.crear(
            nombre="Inversor",
            apellido="Prueba",
            documento="99990002",
        )
        personas.agregar_rol(inversor_id, "INVERSOR")

        ServicioPrestamos(db).crear_completo(
            deudor_id=deudor_id,
            capital=Decimal("1000.00"),
            plazo_meses=3,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 1, 1),
            inversores=[
                {"persona_id": inversor_id, "monto": Decimal("1000.00")},
            ],
            usuario="ui-test",
            tc_inicial=Decimal("1500.00"),
            destino="Prueba UI",
        )

        # Sembramos un evento histórico de recálculo para ejercitar el detalle
        # completo en la aceptación de UI.
        db.ejecutar(
            """
            INSERT INTO pagos
            (prestamo_id, fecha_real, fecha_valor, fecha_registro,
             monto_moneda_pago, monto_moneda_contractual, estado,
             creado_por, tipo_pago)
            VALUES (?, '2026-02-01', '2026-02-01', '2026-02-01',
                    '50.00', '50.00', 'VALIDA', 'ui-test', 'ADELANTO_RAI')
            """,
            (1,),
        )
        pago_id = db.ultimo_id_insertado()
        db.ejecutar(
            """
            INSERT INTO historial_recalculos
            (prestamo_id, pago_id, tipo, fecha, capital_antes, capital_despues,
             cuotas_antes, cuotas_despues, intereses_antes, intereses_despues,
             detalle_json, creado_en, cuota_objetivo_numero)
            VALUES (?, ?, 'RAI', '2026-02-01', '700.00', '650.00',
                    3, 3, '30.00', '20.00', '{"origen":"ui-test"}',
                    '2026-02-01', 1)
            """,
            (1, pago_id),
        )

    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta))
    return ruta


def _run_app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=10)
    at.run()
    assert not at.exception
    return at


def _go_to(at: AppTest, pagina: str) -> AppTest:
    at.segmented_control(key="pagina").set_value(pagina)
    at.run()
    assert not at.exception
    assert at.session_state["pagina"] == pagina
    return at


def _markdown_contains(at: AppTest, text: str) -> bool:
    return any(text in str(x.value) for x in at.markdown)


def test_ui_expone_operador_declarado(app_database: Path, monkeypatch):
    monkeypatch.setenv("PRESTAMOS_OPERADOR", "tester-ui")
    at = _run_app()
    assert not at.exception
    assert at.text_input(key="operador").value == "tester-ui"


def test_arranque_y_resumen_son_operativos(app_database: Path):
    at = _run_app()

    assert at.session_state["pagina"] == "resumen"
    assert at.segmented_control(key="pagina").value == "resumen"


@pytest.mark.parametrize(
    ("pagina", "texto_esperado"),
    [
        ("mi_espacio", "Hola, Javier Prueba"),
        ("planificar", "Planificar"),
        ("escenarios", "Escenarios"),
        ("rendimiento", "Rendimiento"),
        ("prestamos", "Tenés 1 préstamo activo"),
        ("motor_v3", "Motor de Pagos V3"),
        ("analisis", "Análisis financiero"),
        ("pagos", "Historial de pagos"),
        ("operacion", "Operación"),
        ("personas", "Personas"),
        ("auditoria", "Auditoría"),
    ],
)
def test_todas_las_areas_principales_renderizan_sin_excepcion(
    app_database: Path,
    pagina: str,
    texto_esperado: str,
):
    at = _go_to(_run_app(), pagina)

    if pagina in {"planificar", "escenarios"}:
        assert at.title[0].value == texto_esperado
    else:
        assert _markdown_contains(at, texto_esperado)

    if pagina == "motor_v3":
        assert at.segmented_control(key="sombra_incidencias_tipo").value == "TODAS"
        assert _markdown_contains(at, "Readiness de canary")


def test_detalle_financiero_es_alcanzable_desde_el_prestamo(
    app_database: Path,
):
    at = _go_to(_run_app(), "prestamos")

    at.button(key="ver_prestamo_1").click()
    at.run()
    assert not at.exception
    assert at.session_state["prestamo_seleccionado"] == 1

    at.button(key="detalle_financiero_1").click()
    at.run()
    assert not at.exception
    assert at.session_state["pagina"] == "detalle_financiero"
    assert _markdown_contains(at, "Detalle financiero")


def test_detalle_financiero_expone_todas_sus_pestanas(
    app_database: Path,
):
    at = _go_to(_run_app(), "prestamos")

    at.button(key="ver_prestamo_1").click()
    at.run()
    assert not at.exception

    at.button(key="detalle_financiero_1").click()
    at.run()
    assert not at.exception

    etiquetas = [tab.label for tab in at.tabs]
    assert etiquetas == [
        "Amortización",
        "Capital",
        "Devengamientos",
        "Recálculos",
    ]
    assert _markdown_contains(at, "Recálculos RAI/RNI")


def test_navegacion_ida_y_vuelta_conserva_el_estado(
    app_database: Path,
):
    at = _run_app()

    for pagina in (
        "mi_espacio",
        "planificar",
        "escenarios",
        "rendimiento",
        "prestamos",
        "motor_v3",
        "analisis",
        "pagos",
        "operacion",
        "resumen",
    ):
        _go_to(at, pagina)
        assert not at.exception


def test_cambio_de_modo_requiere_confirmacion_y_persiste(
    app_database: Path,
):
    at = _go_to(_run_app(), "motor_v3")

    at.segmented_control(key="motor_pago_modo_solicitado").set_value("LEGACY")
    at.run()
    assert not at.exception

    assert at.text_input(key="motor_pago_motivo_cambio").value == ""
    assert _markdown_contains(at, "El cambio todavía no está aplicado.")

    at.text_input(key="motor_pago_motivo_cambio").set_value(
        "Rollback operativo de prueba"
    )
    at.run()
    assert not at.exception

    at.button(key="aplicar_modo_motor_pago").click()
    at.run()
    assert not at.exception
    assert at.segmented_control(
        key="motor_pago_modo_solicitado"
    ).value == "LEGACY"

    with BaseDatos(app_database) as db:
        fila = db.consultar_uno(
            "SELECT modo, revision FROM configuracion_motor_pago WHERE id = 1"
        )
    assert fila["modo"] == "LEGACY"
    assert fila["revision"] == 2


def test_auditoria_permite_filtrar_e_inspeccionar_correlacion(
    app_database: Path,
):
    at = _go_to(_run_app(), "auditoria")

    assert not at.exception
    assert _markdown_contains(at, "Trazabilidad de cambios y decisiones del sistema")
    assert len(at.selectbox(key="auditoria_operacion").options) > 1
    assert len(at.selectbox(key="auditoria_entidad").options) > 1
    assert at.selectbox(key="auditoria_evento_seleccionado").options

    at.selectbox(key="auditoria_entidad").set_value("PRESTAMO")
    at.run()
    assert not at.exception
    assert _markdown_contains(at, "Detalle del evento")
    assert _markdown_contains(at, "Operación completa")


def test_exportaciones_visibles_en_pantallas_operativas(app_database: Path):
    at = _go_to(_run_app(), "auditoria")
    assert not at.exception
    assert at.download_button(key="auditoria_descargar_csv")

    at = _go_to(at, "personas")
    assert not at.exception
    assert at.download_button(key="personas_descargar_csv")

    at = _go_to(at, "prestamos")
    at.button(key="ver_prestamo_1").click()
    at.run()
    assert not at.exception
    at.button(key="detalle_financiero_1").click()
    at.run()
    assert not at.exception
    assert at.download_button(key="detalle_exportar_amortizacion_1")


def test_mi_espacio_muestra_explicacion_y_glosario(app_database: Path):
    at = _go_to(_run_app(), "mi_espacio")
    assert not at.exception
    assert at.title[0].value == "Mi espacio"
    assert _markdown_contains(at, "Hola, Javier Prueba")
    assert _markdown_contains(at, "Es el dinero original del préstamo.")


def test_mi_espacio_muestra_posicion_financiera_y_evolucion(
    app_database: Path,
):
    at = _go_to(_run_app(), "mi_espacio")
    assert not at.exception
    assert any(x.value == "Tu posición financiera" for x in at.subheader)
    assert any("No representa todo tu patrimonio" in str(x.value) for x in at.caption)
    assert any(
        "La evolución muestra el movimiento acumulado de caja registrado"
        in str(x.value)
        for x in at.caption
    )


def test_planificar_muestra_horizonte_y_limites(app_database: Path):
    at = _go_to(_run_app(), "planificar")
    assert not at.exception
    assert at.title[0].value == "Planificar"
    assert any(
        "Una mirada sencilla a los cobros y pagos que ya conocemos." in str(x.value)
        for x in at.caption
    )
    assert any(
        "Este plan" in str(x.value) and "no" in str(x.value)
        for x in at.markdown
    )


def test_escenarios_muestra_pagina_y_explicacion(app_database: Path):
    at = _go_to(_run_app(), "escenarios")
    assert not at.exception
    assert at.title[0].value == "Escenarios"
    assert any(
        "Un escenario no predice el futuro" in str(x.value)
        for x in at.markdown
    )


def test_rendimiento_muestra_pagina_y_explicacion(app_database: Path):
    at = _go_to(_run_app(), "rendimiento")
    assert not at.exception
    assert at.title[0].value == "Rendimiento"
    assert any(
        "Qué rendimiento o costo muestran los movimientos que realmente ocurrieron."
        in str(x.value)
        for x in at.caption
    )
    assert any(
        "Una tasa histórica no garantiza" in str(x.value)
        for x in at.markdown
    )
