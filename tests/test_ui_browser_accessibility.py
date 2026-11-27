"""Aceptación Chromium de navegación por teclado y layout adaptable.

Inicia el Streamlit real con una SQLite sintética vacía y una cuenta ADMIN.
Verifica la semántica del menú, el foco visible, la activación por teclado y
la ausencia de desbordamiento horizontal en anchos representativos.
No inspecciona ni modifica reglas financieras.
"""

from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from tests.ui_auth_helpers import PASSWORD_TEST, preparar_admin_local


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "ui" / "app.py"


def _puerto_local_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _crear_base_sintetica_vacia(ruta: Path) -> None:
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
    preparar_admin_local(ruta)


def _detener_streamlit(proceso: subprocess.Popen | None) -> None:
    if proceso is None or proceso.poll() is not None:
        return
    proceso.terminate()
    try:
        proceso.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proceso.kill()
        proceso.wait(timeout=5)


def _iniciar_streamlit(ruta_db: Path) -> tuple[subprocess.Popen, str]:
    puerto = _puerto_local_libre()
    url = f"http://127.0.0.1:{puerto}"
    entorno = os.environ.copy()
    entorno["PRESTAMOS_DB_PATH"] = str(ruta_db)
    entorno["PRESTAMOS_AUTH_MODE"] = "local"
    entorno["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    entorno["PYTHONUNBUFFERED"] = "1"

    proceso = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(APP),
            "--server.address=127.0.0.1",
            f"--server.port={puerto}",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ],
        cwd=ROOT,
        env=entorno,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    try:
        limite = time.monotonic() + 60
        ultimo_error: Exception | None = None
        while time.monotonic() < limite:
            if proceso.poll() is not None:
                raise AssertionError(
                    "Streamlit terminó antes de estar disponible "
                    f"(código {proceso.returncode})"
                )
            try:
                with urlopen(url, timeout=1) as respuesta:
                    if respuesta.status == 200:
                        return proceso, url
            except (URLError, TimeoutError, OSError) as exc:
                ultimo_error = exc
            time.sleep(0.25)
        raise AssertionError(
            f"Streamlit no estuvo disponible en {url}; último error: {ultimo_error}"
        )
    except Exception:
        _detener_streamlit(proceso)
        raise


def test_chromium_navegacion_usa_teclado_y_se_adapta_a_varios_anchos(
    tmp_path: Path,
) -> None:
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="Instalá requirements-browser.txt para la aceptación Chromium",
    )

    ruta_db = tmp_path / "browser-accessibility.db"
    _crear_base_sintetica_vacia(ruta_db)
    proceso = None

    try:
        proceso, url = _iniciar_streamlit(ruta_db)
        with playwright.sync_playwright() as motor:
            navegador = motor.chromium.launch()
            try:
                pagina = navegador.new_page(
                    viewport={"width": 1440, "height": 1000}
                )
                pagina.set_default_timeout(20_000)
                pagina.goto(url, wait_until="domcontentloaded")

                pagina.get_by_label("Usuario").fill("admin")
                pagina.get_by_label("Contraseña").fill(PASSWORD_TEST)
                pagina.get_by_role("button", name="Ingresar", exact=True).click()

                barra = pagina.locator('[data-testid="stSidebar"]')
                barra.get_by_role(
                    "heading", name="Préstamos Privados", exact=True
                ).wait_for(state="visible")

                for grupo in (
                    "Inicio",
                    "Cartera",
                    "Análisis e informes",
                    "Administración",
                    "Avanzado",
                ):
                    barra.get_by_role(
                        "heading", name=grupo, exact=True
                    ).wait_for(state="visible")

                # El tema oscuro es la preferencia predeterminada del producto.
                fondo = pagina.locator(".stApp").evaluate(
                    "(elemento) => getComputedStyle(elemento).backgroundColor"
                )
                assert fondo == "rgb(15, 23, 42)"

                # Iniciar foco en el primer destino y avanzar solo con Tab.
                # El siguiente control debe ser Mi espacio y recibir el estilo
                # visible de foco destinado a usuarios de teclado.
                boton_resumen = barra.get_by_role(
                    "button", name="Resumen"
                ).first
                boton_resumen.focus()
                pagina.keyboard.press("Tab")

                boton_enfocado = barra.locator("button:focus-visible")
                assert boton_enfocado.count() == 1
                assert "Mi espacio" in (boton_enfocado.inner_text() or "")
                estado_foco = boton_enfocado.evaluate(
                    "(elemento) => ({"
                    "visible: elemento.matches(\':focus-visible\'),"
                    "ancho: getComputedStyle(elemento).outlineWidth"
                    "})"
                )
                assert estado_foco == {"visible": True, "ancho": "3px"}

                # Activar la ruta con Enter, sin hacer click con el mouse.
                pagina.keyboard.press("Enter")
                pagina.get_by_text(
                    "Tu cuenta todavía no está vinculada a una persona",
                    exact=True,
                ).wait_for(state="visible")

                # Escritorio ancho, notebook, tablet y ventana pequeña.
                for ancho in (1440, 1024, 768, 390):
                    pagina.set_viewport_size(
                        {"width": ancho, "height": 900}
                    )
                    pagina.wait_for_timeout(150)
                    dimensiones = pagina.evaluate(
                        """() => {
                            const raiz = document.documentElement;
                            const principal = document.querySelector(".main");
                            const contenedor = document.querySelector(
                                ".main .block-container"
                            );
                            return {
                                documento: raiz.scrollWidth,
                                documentoVisible: raiz.clientWidth,
                                principal: principal.scrollWidth,
                                principalVisible: principal.clientWidth,
                                contenedor: contenedor.scrollWidth,
                                contenedorVisible: contenedor.clientWidth
                            };
                        }"""
                    )
                    assert dimensiones["documento"] <= (
                        dimensiones["documentoVisible"] + 2
                    ), f"Desbordamiento de documento a {ancho}px: {dimensiones}"
                    assert dimensiones["principal"] <= (
                        dimensiones["principalVisible"] + 2
                    ), f"Desbordamiento del contenido principal a {ancho}px: {dimensiones}"
                    assert dimensiones["contenedor"] <= (
                        dimensiones["contenedorVisible"] + 2
                    ), f"Desbordamiento del contenedor a {ancho}px: {dimensiones}"
            finally:
                navegador.close()
    finally:
        _detener_streamlit(proceso)
