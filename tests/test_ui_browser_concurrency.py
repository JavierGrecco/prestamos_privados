"""Aceptación de concurrencia de pagos con dos sesiones Chromium reales.

Levanta un único proceso Streamlit sobre una SQLite sintética y abre dos
contextos de navegador aislados. La sesión A confirma un pago; la sesión B
conserva el preview anterior e intenta confirmar una intención nueva. La UI
debe detectar la revisión obsoleta, bloquear el segundo pago y exigir una
revisión explícita antes de volver a habilitar la confirmación.

La idempotencia de un retry con resultado incierto se cubre en AppTest y en
servicios; esta prueba se concentra en la frontera real navegador/WebSocket.
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
import re

import pytest

from infraestructura.composicion.prestamos import crear_servicio_prestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo
from tests.ui_auth_helpers import PASSWORD_TEST, preparar_admin_local


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "ui" / "app.py"
NOMBRE_DEUDOR = "Deudor Browser"


def _crear_base_sintetica(ruta: Path) -> int:
    """Crea una cartera mínima: un deudor, un inversor y un préstamo activo."""
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)

        deudor_id = personas.crear(
            nombre="Deudor",
            apellido="Browser",
            documento="99992001",
        )
        personas.agregar_rol(deudor_id, "DEUDOR")

        inversor_id = personas.crear(
            nombre="Inversor Browser",
            apellido="Concurrencia",
            documento="99992002",
        )
        personas.agregar_rol(inversor_id, "INVERSOR")

        crear_servicio_prestamos(db).crear_completo(
            deudor_id=deudor_id,
            capital=Decimal("100000.00"),
            plazo_meses=3,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date.today().replace(day=1),
            inversores=[
                {"persona_id": inversor_id, "monto": Decimal("100000.00")},
            ],
            usuario="browser-concurrency-test",
            tc_inicial=Decimal("1500.00"),
            destino="Aceptación de concurrencia",
        )

        prestamo = db.consultar_uno(
            "SELECT id FROM prestamos WHERE deudor_id = ? ORDER BY id DESC LIMIT 1",
            (deudor_id,),
        )
        assert prestamo is not None
        prestamo_id = int(prestamo["id"])

    # La cuenta local ADMIN se vincula al primer registro (el deudor sintético).
    preparar_admin_local(ruta)
    return prestamo_id


def _puerto_local_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _esperar_streamlit(proceso: subprocess.Popen, url: str) -> None:
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
                    return
        except (URLError, TimeoutError, OSError) as exc:
            ultimo_error = exc
        time.sleep(0.25)

    raise AssertionError(
        f"Streamlit no estuvo disponible en {url}; último error: {ultimo_error}"
    )


def _estado_prestamo(ruta: Path, prestamo_id: int) -> tuple[int, int]:
    with BaseDatos(ruta) as db:
        prestamo = db.consultar_uno(
            "SELECT revision_prestamo FROM prestamos WHERE id = ?",
            (prestamo_id,),
        )
        pagos = db.consultar_uno(
            "SELECT COUNT(*) AS cantidad FROM pagos WHERE prestamo_id = ?",
            (prestamo_id,),
        )
        assert prestamo is not None and pagos is not None
        return int(prestamo["revision_prestamo"]), int(pagos["cantidad"])


def _esperar_estado(
    ruta: Path,
    prestamo_id: int,
    *,
    revision: int,
    cantidad_pagos: int,
    timeout: float = 25,
) -> None:
    limite = time.monotonic() + timeout
    ultimo_estado = None

    while time.monotonic() < limite:
        ultimo_estado = _estado_prestamo(ruta, prestamo_id)
        if ultimo_estado == (revision, cantidad_pagos):
            return
        time.sleep(0.2)

    raise AssertionError(
        "El estado persistido no alcanzó el resultado esperado: "
        f"esperado={(revision, cantidad_pagos)}, actual={ultimo_estado}"
    )


def _autenticar_y_abrir_preview(pagina, url: str) -> None:
    """Inicia una sesión independiente y abre el preview del mismo préstamo."""
    pagina.set_default_timeout(25_000)
    pagina.goto(url, wait_until="domcontentloaded")

    pagina.get_by_label("Usuario").fill("admin")
    pagina.get_by_label("Contraseña").fill(PASSWORD_TEST)
    pagina.get_by_role("button", name="Ingresar", exact=True).click()

    # En la pantalla inicial, la persona no se elige arbitrariamente.
    selector_persona = pagina.get_by_role("combobox").first
    selector_persona.wait_for(state="visible")
    selector_persona.click()
    pagina.get_by_role("option", name=NOMBRE_DEUDOR, exact=True).click()

    barra = pagina.locator('[data-testid="stSidebar"]')
    boton_prestamos = barra.get_by_role(
        "button",
        name=re.compile(r"Préstamos"),
    )
    boton_prestamos.wait_for(state="visible")
    boton_prestamos.click()

    pagina.get_by_role("button", name="Ver detalle", exact=True).click()
    pagina.get_by_role("button", name="Registrar pago", exact=True).click()
    pagina.get_by_text("Preview canónico del Motor V3", exact=True).wait_for(
        state="visible"
    )
    boton_confirmar = pagina.get_by_role(
        "button",
        name="Confirmar pago",
        exact=True,
    )
    boton_confirmar.wait_for(state="visible")
    assert boton_confirmar.is_enabled(), (
        "El preview inicial de la sesión debería permitir confirmar"
    )


def test_dos_contextos_chromium_bloquean_un_pago_con_preview_obsoleto(
    tmp_path: Path,
) -> None:
    """Una segunda sesión real no puede registrar sobre una revisión vencida."""
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="Instalá requirements-browser.txt para la aceptación Chromium",
    )

    ruta_db = tmp_path / "browser-concurrency.db"
    prestamo_id = _crear_base_sintetica(ruta_db)
    revision_inicial, pagos_iniciales = _estado_prestamo(ruta_db, prestamo_id)
    assert pagos_iniciales == 0

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

    navegador = None
    contexto_a = None
    contexto_b = None
    try:
        _esperar_streamlit(proceso, url)

        with playwright.sync_playwright() as motor:
            navegador = motor.chromium.launch()
            # Cada contexto tiene cookies y almacenamiento separados. Ambos
            # se conectan al mismo proceso Streamlit y al mismo archivo SQLite.
            contexto_a = navegador.new_context()
            contexto_b = navegador.new_context()
            pagina_a = contexto_a.new_page()
            pagina_b = contexto_b.new_page()

            _autenticar_y_abrir_preview(pagina_a, url)
            _autenticar_y_abrir_preview(pagina_b, url)

            # Las dos pantallas ya calcularon el preview antes de que cambie
            # la revisión compartida. A confirma primero su pago válido.
            pagina_a.get_by_role(
                "button",
                name="Confirmar pago",
                exact=True,
            ).click()
            _esperar_estado(
                ruta_db,
                prestamo_id,
                revision=revision_inicial + 1,
                cantidad_pagos=1,
            )

            # B conserva su preview anterior en su propia sesión de navegador.
            # Su intento desencadena un rerun y la validación de revisión.
            pagina_b.get_by_role(
                "button",
                name="Confirmar pago",
                exact=True,
            ).click()

            aviso_obsoleto = pagina_b.get_by_text(
                "El préstamo cambió desde que se calculó este pago.",
                exact=False,
            )
            aviso_obsoleto.wait_for(state="visible")

            actualizar = pagina_b.get_by_role(
                "button",
                name="Actualizar cálculo y revisar",
                exact=True,
            )
            actualizar.wait_for(state="visible")
            confirmar_b = pagina_b.get_by_role(
                "button",
                name="Confirmar pago",
                exact=True,
            )
            assert confirmar_b.is_disabled(), (
                "La UI debe bloquear la confirmación hasta revisar el nuevo preview"
            )

            # La revisión obsoleta no debe crear pago, auditoría ni avance extra.
            assert _estado_prestamo(ruta_db, prestamo_id) == (
                revision_inicial + 1,
                1,
            )

            # Solo después de actualizar y revisar el preview vuelve a habilitarse
            # una nueva intención. No se confirma esa segunda operación.
            actualizar.click()
            confirmar_b.wait_for(state="visible")
            assert confirmar_b.is_enabled()
            assert _estado_prestamo(ruta_db, prestamo_id) == (
                revision_inicial + 1,
                1,
            )
    finally:
        if contexto_b is not None:
            contexto_b.close()
        if contexto_a is not None:
            contexto_a.close()
        if navegador is not None:
            navegador.close()
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()
            proceso.wait(timeout=5)
