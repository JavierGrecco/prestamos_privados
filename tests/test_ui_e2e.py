"""Pruebas end-to-end de arranque y navegación de la UI.

Usan AppTest para ejecutar la aplicación real sin navegador. La base de datos
se crea en un directorio temporal y se inyecta mediante PRESTAMOS_DB_PATH.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


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


def _ejecutar_app(app_database: Path) -> AppTest:
    at = AppTest.from_file(
        Path(__file__).resolve().parents[1] / "ui" / "app.py",
        default_timeout=10,
    )
    at.run()
    assert not at.exception, at.exception
    return at


def _seleccionar_pagina(at: AppTest, pagina: str) -> AppTest:
    at.segmented_control(key="pagina").set_value(pagina)
    at.run()
    assert not at.exception, at.exception
    return at


def test_arranque_ui_y_resumen_son_operativos(app_database: Path):
    at = _ejecutar_app(app_database)

    assert at.session_state["pagina"] == "resumen"
    assert any(
        getattr(element, "value", "") == "Resumen"
        for element in at.segmented_control
    )


@pytest.mark.parametrize(
    ("pagina", "texto_esperado"),
    [
        ("prestamos", "Préstamos"),
        ("motor_v3", "Motor de Pagos V3"),
        ("analisis", "Análisis financiero"),
        ("pagos", "Historial de pagos"),
        ("operacion", "Operación"),
    ],
)
def test_cada_area_principal_de_la_ui_renderiza_sin_excepcion(
    app_database: Path,
    pagina: str,
    texto_esperado: str,
):
    at = _ejecutar_app(app_database)
    _seleccionar_pagina(at, pagina)

    assert any(
        texto_esperado in str(getattr(element, "value", ""))
        for element in (*at.markdown, *at.title, *at.header, *at.subheader)
    )


def test_navegacion_ida_y_vuelta_conserva_la_sesion(
    app_database: Path,
):
    at = _ejecutar_app(app_database)

    for pagina in ("prestamos", "motor_v3", "analisis", "pagos", "operacion", "resumen"):
        _seleccionar_pagina(at, pagina)
        assert at.session_state["pagina"] == pagina
        assert not at.exception
