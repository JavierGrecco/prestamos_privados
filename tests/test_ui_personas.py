"""Aceptación de la pantalla Personas."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from tests.ui_auth_helpers import iniciar_apptest_autenticado, preparar_admin_local


APP = Path(__file__).resolve().parents[1] / "ui" / "app.py"


def test_admin_llega_a_personas_desde_el_estado_vacio(tmp_path, monkeypatch):
    ruta = tmp_path / "personas_vacia.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta))

    at = AppTest.from_file(APP, default_timeout=10)
    iniciar_apptest_autenticado(at, ruta)

    assert not at.exception
    assert at.session_state["pagina"] == "resumen"
    assert at.button(key="ir_a_crear_primera_persona").label == "Crear primera persona"

    at.button(key="ir_a_crear_primera_persona").click()
    at.run()

    assert not at.exception
    assert at.session_state["pagina"] == "personas"
    assert [tab.label for tab in at.tabs] == ["Personas", "Nueva persona", "Administrar"]


def test_lectura_no_recibe_accion_para_crear_primera_persona(tmp_path, monkeypatch):
    ruta = tmp_path / "personas_sin_datos_lectura.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta))

    usuario_id, _ = preparar_admin_local(ruta)
    with BaseDatos(ruta) as db:
        db.ejecutar(
            """
            UPDATE usuarios_app
            SET rol = 'LECTURA', revision_sesion = revision_sesion + 1
            WHERE id = ?
            """,
            (usuario_id,),
        )
        revision = db.consultar_uno(
            "SELECT revision_sesion FROM usuarios_app WHERE id = ?",
            (usuario_id,),
        )["revision_sesion"]

    at = AppTest.from_file(APP, default_timeout=10)
    at.session_state["usuario_app_id"] = usuario_id
    at.session_state["usuario_app_revision"] = revision
    at.run()

    assert not at.exception
    assert at.session_state["pagina"] == "resumen"
    assert not any(
        button.key == "ir_a_crear_primera_persona"
        for button in at.button
    )
    assert any(
        "Pedile a un administrador que cree la primera persona."
        in str(markdown.value)
        for markdown in at.markdown
    )


def test_personas_renderiza_un_registro(tmp_path, monkeypatch):
    ruta = tmp_path / "personas.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        db.ejecutar(
            "INSERT INTO personas (nombre, apellido, documento, creado_en) VALUES (?, ?, ?, ?)",
            ("Persona", "Prueba", "90000009", "2026-01-01"),
        )
        persona_id = db.ultimo_id_insertado()
        db.ejecutar(
            "INSERT INTO roles_persona (persona_id, rol, fecha_alta) VALUES (?, 'DEUDOR', ?)",
            (persona_id, "2026-01-01"),
        )
    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta))

    at = AppTest.from_file(APP, default_timeout=10)
    iniciar_apptest_autenticado(at, ruta)
    at.segmented_control(key="pagina").set_value("personas")
    at.run()
    assert not at.exception
    assert any("Persona Prueba" in str(m.value) for m in at.markdown)
