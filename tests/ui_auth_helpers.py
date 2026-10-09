"""Helpers para aceptar el entrypoint protegido por cuentas locales."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from aplicacion.servicios.usuarios_locales import ServicioUsuariosLocales
from infraestructura import BaseDatos


PASSWORD_TEST = "frase-segura-de-pruebas-2026"


def preparar_admin_local(ruta: Path) -> tuple[int, int]:
    """Asegura una cuenta ADMIN sintética en la base de prueba."""
    with BaseDatos(ruta) as db:
        servicio = ServicioUsuariosLocales(db)
        actual = servicio.usuarios.por_username("admin")
        if actual is None:
            servicio.crear_administrador_inicial(
                username="admin",
                nombre="Administrador de prueba",
                password=PASSWORD_TEST,
            )
            actual = servicio.usuarios.por_username("admin")
        if actual is None:
            raise AssertionError("No se pudo preparar el usuario ADMIN de prueba")
        return actual[0].id, actual[0].revision_sesion


def iniciar_apptest_autenticado(at: AppTest, ruta: Path) -> AppTest:
    """Prepara un ID de sesión válido antes del primer rerun de Streamlit."""
    usuario_id, revision_sesion = preparar_admin_local(ruta)
    at.session_state["usuario_app_id"] = usuario_id
    at.session_state["usuario_app_revision"] = revision_sesion
    at.run()
    assert not at.exception
    return at
