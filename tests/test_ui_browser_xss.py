"""Aceptación XSS en Chromium con el entrypoint real de Streamlit.

Este test se ejecuta en el workflow browser-security. La suite habitual lo
omite cuando Playwright no está instalado; no requiere datos productivos.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from infraestructura.composicion.prestamos import crear_servicio_prestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo
from tests.ui_auth_helpers import PASSWORD_TEST, preparar_admin_local


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "ui" / "app.py"


def _crear_base_hostil(ruta: Path) -> tuple[str, str]:
    nombre_malicioso = '<img src=x onerror="alert(\'pp-xss-name\')">'
    destino_malicioso = (
        '</div><img src=x onerror="alert(\'pp-xss-destination\')">'
        '<script>alert("pp-xss-script")</script>'
    )

    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)

        deudor_id = personas.crear(
            nombre="Deudor de prueba",
            apellido="Chromium",
            documento="99993001",
        )
        personas.agregar_rol(deudor_id, "DEUDOR")

        inversor_id = personas.crear(
            nombre="Inversor de prueba",
            apellido="Chromium",
            documento="99993002",
        )
        personas.agregar_rol(inversor_id, "INVERSOR")

        crear_servicio_prestamos(db).crear_completo(
            deudor_id=deudor_id,
            capital=Decimal("10000.00"),
            plazo_meses=3,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date.today(),
            inversores=[
                {"persona_id": inversor_id, "monto": Decimal("10000.00")},
            ],
            usuario="browser-xss-test",
            tc_inicial=Decimal("1500.00"),
            destino="Destino sintético",
        )

    # La cuenta ADMIN local queda vinculada al deudor (primera persona).
    preparar_admin_local(ruta)

    with BaseDatos(ruta) as db:
        db.ejecutar(
            "UPDATE personas SET nombre = ? WHERE id = ?",
            (nombre_malicioso, deudor_id),
        )
        prestamo = db.consultar_uno(
            "SELECT id FROM prestamos ORDER BY id DESC LIMIT 1"
        )
        assert prestamo is not None
        db.ejecutar(
            "UPDATE prestamos SET destino = ? WHERE id = ?",
            (destino_malicioso, prestamo["id"]),
        )

    return nombre_malicioso, destino_malicioso


def _puerto_local_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _esperar_streamlit(proceso: subprocess.Popen, url: str) -> None:
    limite = time.monotonic() + 45
    ultimo_error: Exception | None = None

    while time.monotonic() < limite:
        if proceso.poll() is not None:
            raise AssertionError(
                f"Streamlit terminó antes de estar disponible (código {proceso.returncode})"
            )
        try:
            with urlopen(url, timeout=1) as respuesta:
                if respuesta.status == 200:
                    return
        except (URLError, TimeoutError, OSError) as exc:
            ultimo_error = exc
        time.sleep(0.25)

    raise AssertionError(
        f"Streamlit no estuvo disponible en {url}; último error: {ultimo_error}"
    )


def test_chromium_no_interpreta_html_malicioso_guardado_en_sqlite(
    tmp_path: Path,
):
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="Instalá el extra [browser] para ejecutar la aceptación Chromium",
    )

    ruta_db = tmp_path / "browser-xss.db"
    nombre_malicioso, destino_malicioso = _crear_base_hostil(ruta_db)
    puerto = _puerto_local_libre()
    url = f"http://127.0.0.1:{puerto}"

    entorno = os.environ.copy()
    entorno["PRESTAMOS_DB_PATH"] = str(ruta_db)
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
        _esperar_streamlit(proceso, url)

        alertas: list[str] = []
        with playwright.sync_playwright() as motor:
            navegador = motor.chromium.launch()
            try:
                pagina = navegador.new_page()
                pagina.set_default_timeout(20_000)

                def registrar_dialogo(dialog) -> None:
                    alertas.append(dialog.message)
                    dialog.dismiss()

                pagina.on("dialog", registrar_dialogo)
                pagina.goto(url, wait_until="domcontentloaded")

                pagina.get_by_label("Usuario").fill("admin")
                pagina.get_by_label("Contraseña").fill(PASSWORD_TEST)
                pagina.get_by_role("button", name="Ingresar").click()

                boton_mi_espacio = pagina.get_by_role(
                    "button", name="Mi espacio", exact=False
                )
                boton_mi_espacio.wait_for(state="visible")
                boton_mi_espacio.click()

                saludo = pagina.locator(".saludo")
                saludo.wait_for(state="visible")
                assert nombre_malicioso in (saludo.text_content() or "")
                assert pagina.locator(
                    ".saludo img, .saludo svg, .saludo script"
                ).count() == 0

                destino = pagina.locator(
                    ".bloque-impacto .detalle-item-sub"
                ).filter(has_text="pp-xss-destination")
                destino.wait_for(state="visible")
                assert destino_malicioso in (destino.first.text_content() or "")
                assert pagina.locator(
                    ".bloque-impacto img, "
                    ".bloque-impacto svg, "
                    ".bloque-impacto script"
                ).count() == 0

                # Da oportunidad a que se disparen onerror/onload si alguna
                # etiqueta se hubiera interpretado como HTML ejecutable.
                pagina.wait_for_timeout(750)
                assert alertas == [], (
                    "Se ejecutó un handler JavaScript inesperado: "
                    + ", ".join(alertas)
                )
            finally:
                navegador.close()
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()
            proceso.wait(timeout=5)
