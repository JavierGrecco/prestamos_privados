"""Pruebas de aislamiento de conexiones SQLite entre sesiones Streamlit."""

from __future__ import annotations

from pathlib import Path
import textwrap

from streamlit.testing.v1 import AppTest

from ui.recursos import liberar_recurso_db


ROOT = Path(__file__).resolve().parents[1]


def test_dos_sesiones_streamlit_usan_conexiones_independientes_sobre_el_mismo_archivo(
    tmp_path: Path,
    monkeypatch,
):
    """Cada sesión tiene su BaseDatos; SQLite mantiene los datos compartidos."""
    ruta = tmp_path / "sesiones.db"
    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta))

    probe = tmp_path / "probe_sesion.py"
    probe.write_text(
        textwrap.dedent(
            f"""
            import os
            import sys
            import streamlit as st

            sys.path.insert(0, {str(ROOT)!r})

            from ui.app import abrir_db

            db = abrir_db(os.environ["PRESTAMOS_DB_PATH"])
            db.ejecutar(
                "CREATE TABLE IF NOT EXISTS probe_sesiones "
                "(id INTEGER PRIMARY KEY, valor TEXT NOT NULL)"
            )

            if st.session_state.get("modo") == "escritura":
                with db.transaccion():
                    db.ejecutar(
                        "INSERT INTO probe_sesiones (valor) VALUES (?)",
                        ("escrito-desde-sesion-a",),
                    )

            filas = db.consultar(
                "SELECT valor FROM probe_sesiones ORDER BY id"
            )
            st.session_state["db_identity"] = id(db)
            st.session_state["db_resource"] = db
            st.session_state["valores_visibles"] = [fila["valor"] for fila in filas]
            """
        ),
        encoding="utf-8",
    )

    sesion_a = AppTest.from_file(probe, default_timeout=30)
    sesion_a.session_state["modo"] = "escritura"
    sesion_a.run()
    assert not sesion_a.exception

    sesion_b = AppTest.from_file(probe, default_timeout=30)
    sesion_b.session_state["modo"] = "lectura"
    sesion_b.run()
    assert not sesion_b.exception

    db_a = sesion_a.session_state["db_resource"]
    db_b = sesion_b.session_state["db_resource"]
    try:
        assert sesion_a.session_state["db_identity"] != sesion_b.session_state["db_identity"]
        assert db_a is not db_b
        assert sesion_b.session_state["valores_visibles"] == [
            "escrito-desde-sesion-a"
        ]
    finally:
        # El callback de Streamlit también puede ejecutarse al liberar la
        # sesión. BaseDatos.cerrar() es idempotente y tolera ambos caminos.
        liberar_recurso_db(db_a)
        liberar_recurso_db(db_b)


def test_liberador_cierra_el_recurso_y_es_idempotente(tmp_path: Path):
    from infraestructura import BaseDatos, ErrorConexion

    db = BaseDatos(tmp_path / "liberacion.db")
    db.abrir()

    liberar_recurso_db(db)
    liberar_recurso_db(db)

    try:
        db.consultar("SELECT 1")
    except ErrorConexion:
        pass
    else:
        raise AssertionError("El recurso debía estar cerrado después de liberarlo")
