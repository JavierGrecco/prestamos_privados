"""Aceptación de la pantalla Personas."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones


APP = Path(__file__).resolve().parents[1] / "ui" / "app.py"


def test_personas_es_accesible_con_base_vacia(tmp_path, monkeypatch):
    ruta = tmp_path / "personas_vacia.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta))

    at = AppTest.from_file(APP, default_timeout=10)
    at.run()
    assert not at.exception

    at.segmented_control(key="pagina").set_value("personas")
    at.run()
    assert not at.exception
    assert at.session_state["pagina"] == "personas"
    assert [tab.label for tab in at.tabs] == ["Personas", "Nueva persona", "Administrar"]


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
    at.run()
    assert not at.exception
    at.segmented_control(key="pagina").set_value("personas")
    at.run()
    assert not at.exception
    assert any("Persona Prueba" in str(m.value) for m in at.markdown)
