"""Aceptación end-to-end de la aplicación Streamlit.

Ejecuta el entrypoint real sobre una base SQLite temporal y recorre las áreas
principales de la aplicación sin depender de la base local del desarrollador.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import streamlit as st
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

        javier_id = personas.crear(
            nombre="Javier",
            apellido="Prueba",
            documento="99990001",
        )
        personas.agregar_rol(javier_id, "DEUDOR")
        personas.agregar_rol(javier_id, "INVERSOR")

        inversor_id = personas.crear(
            nombre="Inversor",
            apellido="Prueba",
            documento="99990002",
        )
        personas.agregar_rol(inversor_id, "INVERSOR")

        ServicioPrestamos(db).crear_completo(
            deudor_id=javier_id,
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

    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta))
    return ruta


def _run_app() -> AppTest:
    # abrir_db() utiliza cache_resource. Limpiarlo antes de cada caso garantiza
    # que nunca se reutilice otra base temporal.
    st.cache_resource.clear()
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


def test_arranque_y_resumen_son_operativos(app_database: Path):
    at = _run_app()

    assert at.session_state["pagina"] == "resumen"
    assert at.segmented_control(key="pagina").value == "resumen"


@pytest.mark.parametrize(
    ("pagina", "texto_esperado"),
    [
        ("prestamos", "Tenés 1 préstamo activo"),
        ("motor_v3", "Motor de Pagos V3"),
        ("analisis", "Análisis financiero"),
        ("pagos", "Historial de pagos"),
        ("operacion", "Operación"),
    ],
)
def test_todas_las_areas_principales_renderizan_sin_excepcion(
    app_database: Path,
    pagina: str,
    texto_esperado: str,
):
    at = _go_to(_run_app(), pagina)

    assert _markdown_contains(at, texto_esperado)


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


def test_la_pestana_de_recalculos_del_detalle_no_rompe_la_ui(
    app_database: Path,
):
    at = _go_to(_run_app(), "prestamos")

    at.button(key="ver_prestamo_1").click()
    at.run()
    assert not at.exception

    at.button(key="detalle_financiero_1").click()
    at.run()
    assert not at.exception

    # La pestaña se renderiza aun sin recálculos históricos.
    assert len(at.tabs) == 4
    assert _markdown_contains(at, "Recálculos RAI/RNI")


def test_navegacion_ida_y_vuelta_conserva_el_estado(
    app_database: Path,
):
    at = _run_app()

    for pagina in (
        "prestamos",
        "motor_v3",
        "analisis",
        "pagos",
        "operacion",
        "resumen",
    ):
        _go_to(at, pagina)
        assert not at.exception
