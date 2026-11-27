"""Aceptación Chromium del backup restaurado tras reiniciar Streamlit.

El escenario crea y restaura una base sintética mediante el drill real,
prepara el acceso local, abre el archivo restaurado con un proceso Streamlit,
consulta un pago en Chromium, cierra el proceso y repite la consulta desde un
segundo proceso y una sesión de navegador nueva.
"""

from __future__ import annotations

import hashlib
import json
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
from infraestructura.repositorios import LedgerRepo, PrestamoRepo
from tests.ui_auth_helpers import PASSWORD_TEST, preparar_admin_local


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "ui" / "app.py"
RESTORE_DRILL = ROOT / "scripts" / "restore_drill_sintetico.py"
REFERENCIA_RESTORE = "RESTORE-DRILL-001"
NOTA_RESTORE = "Movimiento generado exclusivamente para el restore drill"


def _sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _puerto_local_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


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


def _consultar_pago_restaurado(pagina, url: str) -> None:
    """Autentica y comprueba la evidencia que sobrevivió al restore/restart."""
    pagina.set_default_timeout(20_000)
    pagina.goto(url, wait_until="domcontentloaded")
    pagina.get_by_label("Usuario").fill("admin")
    pagina.get_by_label("Contraseña").fill(PASSWORD_TEST)
    pagina.get_by_role("button", name="Ingresar", exact=True).click()

    selector_persona = pagina.get_by_role("combobox").first
    selector_persona.wait_for(state="visible")
    selector_persona.click()
    pagina.get_by_role(
        "option",
        name="Deudor Restore Drill",
        exact=True,
    ).click()

    barra = pagina.locator('[data-testid="stSidebar"]')
    barra.get_by_role(
        "button",
        name="○ Pagos",
        exact=True,
    ).click()
    pagina.get_by_text("Historial de pagos", exact=True).wait_for(state="visible")

    boton_detalle = pagina.get_by_role("button", name="Detalle", exact=True)
    boton_detalle.wait_for(state="visible")
    boton_detalle.click()

    pagina.get_by_text("Identidad y resultado", exact=True).wait_for(state="visible")
    referencia = pagina.locator(".detalle-item").filter(
        has_text="Referencia"
    ).locator("strong")
    referencia.wait_for(state="visible")
    assert (referencia.text_content() or "") == REFERENCIA_RESTORE

    nota = pagina.locator(".nota-contextual").filter(
        has_text=NOTA_RESTORE
    )
    nota.wait_for(state="visible")
    assert (nota.locator(".nota-texto").text_content() or "") == NOTA_RESTORE

    # La consulta debe mostrar además evidencia de imputaciones, no solo login.
    pagina.get_by_text("Imputaciones", exact=True).wait_for(state="visible")
    assert pagina.locator(".detalle-titulo").filter(
        has_text="Pago #"
    ).count() == 1


def test_chromium_abre_y_reabre_el_restore_en_proceso_streamlit(
    tmp_path: Path,
):
    """La copia restaurada sigue disponible tras cerrar y recrear Streamlit."""
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="Instalá requirements-browser.txt para la aceptación Chromium",
    )

    directorio_drill = tmp_path / "restore-drill"
    resultado_proceso = subprocess.run(
        [
            sys.executable,
            str(RESTORE_DRILL),
            "--directorio",
            str(directorio_drill),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert resultado_proceso.returncode == 0, (
        resultado_proceso.stderr or resultado_proceso.stdout
    )
    resultado = json.loads(resultado_proceso.stdout)
    assert resultado["ok"] is True
    assert resultado["aceptacion_ui_manual_pendiente"] is True

    rutas = resultado["rutas"]
    ruta_origen = Path(rutas["origen_sintetico"])
    ruta_restore = Path(rutas["restore"])
    assert ruta_restore.is_file()
    assert _sha256(ruta_origen) == resultado["sha256_origen"]

    # El administrador sintético solo se agrega a la copia restaurada.
    preparar_admin_local(ruta_restore)

    proceso_primero = None
    proceso_segundo = None
    try:
        with playwright.sync_playwright() as motor:
            navegador = motor.chromium.launch()
            try:
                proceso_primero, url_primera = _iniciar_streamlit(ruta_restore)
                contexto_primero = navegador.new_context()
                try:
                    pagina_primera = contexto_primero.new_page()
                    _consultar_pago_restaurado(pagina_primera, url_primera)
                finally:
                    contexto_primero.close()

                # Detener el primer proceso antes de iniciar otro proceso
                # independiente sobre el mismo archivo restaurado.
                _detener_streamlit(proceso_primero)
                assert proceso_primero.poll() is not None
                proceso_primero = None

                proceso_segundo, url_segunda = _iniciar_streamlit(ruta_restore)
                contexto_segundo = navegador.new_context()
                try:
                    pagina_segunda = contexto_segundo.new_page()
                    _consultar_pago_restaurado(pagina_segunda, url_segunda)
                finally:
                    contexto_segundo.close()
            finally:
                navegador.close()
    finally:
        _detener_streamlit(proceso_segundo)
        _detener_streamlit(proceso_primero)

    # Navegar y reiniciar no debe crear pagos ni alterar los hechos restaurados.
    with BaseDatos(ruta_restore) as db:
        prestamo = PrestamoRepo(db).obtener(int(resultado["prestamo_id"]))
        cantidad_pagos = db.consultar_uno(
            "SELECT COUNT(*) AS cantidad FROM pagos"
        )
        cantidad_admins = db.consultar_uno(
            "SELECT COUNT(*) AS cantidad FROM usuarios_app"
        )
        assert prestamo is not None
        assert cantidad_pagos["cantidad"] == 1
        assert cantidad_admins["cantidad"] == 1
        assert LedgerRepo(db).verificar_cuadre()

    with BaseDatos(ruta_origen) as db_origen:
        cantidad_admins_origen = db_origen.consultar_uno(
            "SELECT COUNT(*) AS cantidad FROM usuarios_app"
        )
        assert cantidad_admins_origen["cantidad"] == 0
    assert _sha256(ruta_origen) == resultado["sha256_origen"]
