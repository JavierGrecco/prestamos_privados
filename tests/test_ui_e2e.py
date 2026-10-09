"""Aceptación end-to-end de la aplicación Streamlit.

Ejecuta el entrypoint real sobre una base SQLite temporal y recorre las áreas
principales de la aplicación sin depender de la base local del desarrollador.
"""

from __future__ import annotations

from datetime import date
import os
from decimal import Decimal
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo
from tests.ui_auth_helpers import preparar_admin_local


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


def _run_app_without_login() -> AppTest:
    """Ejecuta el entrypoint sin precargar una sesión autenticada."""
    at = AppTest.from_file(APP, default_timeout=10)
    at.run()
    assert not at.exception
    return at


def _run_app(
    rol: str = "ADMIN",
    seleccionar_persona: bool = True,
) -> AppTest:
    ruta = Path(os.environ["PRESTAMOS_DB_PATH"])
    usuario_id, revision_sesion = preparar_admin_local(ruta)
    if rol != "ADMIN":
        with BaseDatos(ruta) as db:
            db.ejecutar(
                """
                UPDATE usuarios_app
                SET rol = ?, revision_sesion = revision_sesion + 1
                WHERE id = ?
                """,
                (rol, usuario_id),
            )
            revision_sesion = db.consultar_uno(
                "SELECT revision_sesion FROM usuarios_app WHERE id = ?",
                (usuario_id,),
            )["revision_sesion"]
    at = AppTest.from_file(APP, default_timeout=10)
    at.session_state["usuario_app_id"] = usuario_id
    at.session_state["usuario_app_revision"] = revision_sesion
    if seleccionar_persona:
        # La fixture tiene una persona de negocio con ID 1. La seleccionamos
        # explícitamente para los escenarios E2E que requieren ese contexto.
        at.session_state["persona_id"] = 1
    at.run()
    assert not at.exception
    return at


def _go_to(at: AppTest, pagina: str) -> AppTest:
    at.button(key=f"nav_{pagina}").click()
    at.run()
    assert not at.exception
    assert at.session_state["pagina"] == pagina
    return at


def _markdown_contains(at: AppTest, text: str) -> bool:
    return any(text in str(x.value) for x in at.markdown)


def test_configuracion_inicial_muestra_selector_de_tema_y_permite_cambiarlo(
    app_database: Path,
):
    at = _run_app_without_login()

    assert any(t.value == "Configurar administrador local" for t in at.title)
    assert at.segmented_control(key="tema").value == "oscuro"

    at.segmented_control(key="tema").set_value("claro")
    at.run()

    assert not at.exception
    assert at.segmented_control(key="tema").value == "claro"
    assert any(t.value == "Configurar administrador local" for t in at.title)


def test_cuenta_existente_muestra_login_sin_ofrecer_otro_admin(
    app_database: Path,
):
    ruta = Path(os.environ["PRESTAMOS_DB_PATH"])
    preparar_admin_local(ruta)

    at = _run_app_without_login()

    assert any(t.value == "Iniciar sesión" for t in at.title)
    assert not any(t.value == "Configurar administrador local" for t in at.title)
    assert at.segmented_control(key="tema").value == "oscuro"

    at.segmented_control(key="tema").set_value("intermedio")
    at.run()

    assert not at.exception
    assert at.segmented_control(key="tema").value == "intermedio"
    with BaseDatos(ruta) as db:
        cantidad = db.consultar_uno(
            "SELECT COUNT(*) AS cantidad FROM usuarios_app"
        )["cantidad"]
    assert cantidad == 1


def test_ui_muestra_la_cuenta_autenticada_y_no_un_operador_editable(app_database: Path):
    at = _run_app()
    assert not at.exception
    assert at.session_state["operador"] == "admin"
    assert any("admin · ADMIN" in str(x.value) for x in at.caption)
    assert at.button(key="cerrar_sesion_local")
    assert not any(getattr(x, "key", None) == "operador" for x in at.text_input)


def test_cerrar_sesion_desde_el_menu_de_cuenta_vuelve_al_login(app_database: Path):
    at = _run_app()

    at.button(key="cerrar_sesion_local").click()
    at.run()

    assert not at.exception
    assert "usuario_app_id" not in at.session_state
    assert "usuario_app_revision" not in at.session_state
    assert any(t.value == "Iniciar sesión" for t in at.title)


def test_pantallas_administrativas_no_muestran_selector_de_persona_global(
    app_database: Path,
):
    at = _go_to(_run_app(), "personas")

    assert not at.exception
    assert not any(
        getattr(widget, "key", None) == "persona_id"
        for widget in at.selectbox
    )
    assert at.button(key="nav_usuarios")


def test_ui_cierra_sesion_abierta_si_cambia_revision_de_seguridad(
    app_database: Path,
):
    at = _run_app()
    usuario_id = at.session_state["usuario_app_id"]
    revision = at.session_state["usuario_app_revision"]

    with BaseDatos(app_database) as db:
        db.ejecutar(
            """
            UPDATE usuarios_app
            SET revision_sesion = revision_sesion + 1
            WHERE id = ?
            """,
            (usuario_id,),
        )
        nueva_revision = db.consultar_uno(
            "SELECT revision_sesion FROM usuarios_app WHERE id = ?",
            (usuario_id,),
        )["revision_sesion"]

    assert nueva_revision == revision + 1
    at.run()

    assert not at.exception
    assert "usuario_app_id" not in at.session_state
    assert "usuario_app_revision" not in at.session_state
    assert any(t.value == "Iniciar sesión" for t in at.title)


def test_arranque_y_resumen_son_operativos(app_database: Path):
    at = _run_app()

    assert at.session_state["pagina"] == "resumen"
    assert at.button(key="nav_resumen")


def test_inicio_no_preselecciona_una_persona_arbitrariamente(
    app_database: Path,
):
    at = _run_app(seleccionar_persona=False)

    assert not at.exception
    assert at.session_state["persona_id"] is None
    assert at.selectbox(key="persona_id").value is None
    assert _markdown_contains(at, "Elegí una persona para continuar")

    at.selectbox(key="persona_id").set_value(1)
    at.run()
    assert not at.exception
    assert at.session_state["persona_id"] == 1
    assert _markdown_contains(at, "Hola, Javier")


@pytest.mark.parametrize(
    ("pagina", "texto_esperado"),
    [
        ("mi_espacio", "Hola, Javier Prueba"),
        ("planificar", "Planificar"),
        ("simular_carencia", "Simulador de carencia inicial"),
        ("escenarios", "Escenarios"),
        ("rendimiento", "Rendimiento"),
        ("reportes", "Reportes"),
        ("comparar", "Comparar"),
        ("prestamos", "Tenés 1 préstamo activo"),
        ("motor_v3", "Motor de Pagos V3"),
        ("analisis", "Análisis financiero"),
        ("pagos", "Historial de pagos"),
        ("operacion", "Operación"),
        ("personas", "Personas"),
        ("auditoria", "Auditoría"),
        ("usuarios", "Administrar usuarios"),
    ],
)
def test_todas_las_areas_principales_renderizan_sin_excepcion(
    app_database: Path,
    pagina: str,
    texto_esperado: str,
):
    at = _go_to(_run_app(), pagina)

    if pagina in {"planificar", "escenarios", "rendimiento", "reportes", "comparar", "usuarios", "simular_carencia"}:
        assert at.title[0].value == texto_esperado
    else:
        assert _markdown_contains(at, texto_esperado)

    if pagina == "motor_v3":
        assert at.segmented_control(key="sombra_incidencias_tipo").value == "TODAS"
        assert _markdown_contains(at, "Readiness de canary")


def test_simulador_carencia_no_persiste_ni_modifica_prestamos(app_database: Path):
    ruta = Path(os.environ["PRESTAMOS_DB_PATH"])
    with BaseDatos(ruta) as db:
        antes = db.consultar_uno("SELECT COUNT(*) AS n FROM prestamos")["n"]

    at = _go_to(_run_app(seleccionar_persona=False), "simular_carencia")

    assert not at.exception
    assert at.title[0].value == "Simulador de carencia inicial"
    assert at.session_state["pagina"] == "simular_carencia"
    assert len(at.dataframe) >= 2
    assert at.selectbox(key="sim_carencia_detalle").value == "SIN_INTERES"

    at.selectbox(key="sim_carencia_detalle").set_value("DIFERIR_SIMPLE_DISTRIBUIDO")
    at.run()
    assert not at.exception
    assert any("Interés diferido sin capitalizar" in str(getattr(x, "label", "")) for x in at.metric)

    at.selectbox(key="sim_carencia_convencion").set_value("ACTUAL_365")
    at.run()
    assert not at.exception
    assert at.selectbox(key="sim_carencia_convencion").value == "ACTUAL_365"
    assert len(at.dataframe) >= 2

    with BaseDatos(ruta) as db:
        despues = db.consultar_uno("SELECT COUNT(*) AS n FROM prestamos")["n"]
    assert despues == antes

    # El nuevo modo USD conserva el carácter analítico y convierte cuota a cuota
    # solo cuando se activa una trayectoria de tipo de cambio proyectada.
    at.radio(key="sim_carencia_unidad").set_value(
        "USD de referencia — solo análisis"
    )
    at.run()
    assert not at.exception
    assert any("Plan de reposición en USD" in x.value for x in at.subheader)
    assert len(at.dataframe) >= 1
    assert any(
        "No crea una obligación legal en dólares" in str(x.value)
        for x in at.info
    )

    at.checkbox(key="sim_usd_usar_proyeccion").set_value(True)
    at.run()
    assert not at.exception
    assert any(
        "escenarios proyectados" in str(getattr(x, "value", "")).lower()
        for x in at.warning
    )
    assert len(at.dataframe) >= 1

    with BaseDatos(ruta) as db:
        despues_modo_usd = db.consultar_uno(
            "SELECT COUNT(*) AS n FROM prestamos"
        )["n"]
    assert despues_modo_usd == antes


def test_detalle_financiero_es_alcanzable_desde_el_prestamo(
    app_database: Path,
):
    at = _go_to(_run_app(), "prestamos")

    at.button(key="ver_prestamo_1").click()
    at.run()
    assert not at.exception
    assert at.session_state["prestamo_seleccionado"] == 1
    assert _markdown_contains(at, "Garantías personales")
    assert _markdown_contains(at, "Registrar una garantía")

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
        "reportes",
        "comparar",
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


def test_reportes_muestra_vista_y_descargas(app_database: Path):
    at = _go_to(_run_app(), "reportes")
    assert not at.exception
    assert at.title[0].value == "Reportes"
    assert at.download_button(key="reporte_descargar_markdown")
    assert at.download_button(key="reporte_descargar_json")
    assert at.download_button(key="reporte_descargar_csv")
    assert _markdown_contains(at, "Posición conocida")
    assert _markdown_contains(at, "Plan futuro")


def test_mi_espacio_requiere_persona_vinculada_y_no_toma_el_selector_global(
    app_database: Path,
):
    at = _run_app()
    usuario_id = at.session_state["usuario_app_id"]

    # La fixture parte con persona global seleccionada y cuenta vinculada.
    # Quitamos el vínculo de la cuenta y actualizamos la revisión que la sesión
    # guardaría después de un nuevo login; mantenemos persona_id=1 para probar
    # que Mi espacio no toma ese valor como identidad personal.
    with BaseDatos(app_database) as db:
        db.ejecutar(
            """
            UPDATE usuarios_app
            SET persona_id = NULL, revision_sesion = revision_sesion + 1
            WHERE id = ?
            """,
            (usuario_id,),
        )
        revision = db.consultar_uno(
            "SELECT revision_sesion FROM usuarios_app WHERE id = ?",
            (usuario_id,),
        )["revision_sesion"]

    at.session_state["usuario_app_revision"] = revision
    assert at.session_state["persona_id"] == 1
    at = _go_to(at, "mi_espacio")

    assert not at.exception
    assert _markdown_contains(at, "Tu cuenta todavía no está vinculada a una persona")
    assert not _markdown_contains(at, "Hola, Javier")
    assert at.session_state["persona_id"] == 1


def test_acceso_personal_respetar_allowlist(app_database: Path, monkeypatch):
    monkeypatch.setenv("PRESTAMOS_PERSONAS_PERMITIDAS", "999999")
    at = _go_to(_run_app(), "mi_espacio")
    assert not at.exception
    assert _markdown_contains(
        at,
        "No hay una persona autorizada para esta pantalla.",
    )


def test_rol_lectura_oculta_superficies_operativas_y_administrativas(
    app_database: Path,
):
    at = _run_app(rol="LECTURA")
    opciones = {button.key.removeprefix("nav_") for button in at.button if button.key and button.key.startswith("nav_")}
    assert "resumen" in opciones
    assert "mi_espacio" in opciones
    assert "reportes" in opciones
    assert "auditoria" not in opciones
    assert "motor_v3" not in opciones
    assert "operacion" not in opciones
    assert "usuarios" not in opciones
    assert "personas" not in opciones
    assert "prestamos" not in opciones
    assert "pagos" not in opciones


def test_lectura_no_puede_abrir_usuarios_cambiando_la_ruta(
    app_database: Path,
):
    at = _run_app(rol="LECTURA")

    # Simula intentar una ruta administrativa desde la sesión, sin usar el menú.
    at.session_state["pagina"] = "usuarios"
    at.run()

    assert not at.exception
    assert at.session_state["pagina"] != "usuarios"
    opciones = {
        button.key.removeprefix("nav_")
        for button in at.button
        if button.key and button.key.startswith("nav_")
    }
    assert "usuarios" not in opciones
    assert not _markdown_contains(at, "Administrar usuarios")
