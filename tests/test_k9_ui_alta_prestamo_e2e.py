"""Aceptación end-to-end del alta de préstamos desde Streamlit."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
import ast

import pytest
from streamlit.testing.v1 import AppTest

from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


APP = Path(__file__).resolve().parents[1] / "ui" / "app.py"


@pytest.fixture
def alta_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ruta = tmp_path / "alta-ui.db"

    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)

        deudor_id = personas.crear(
            nombre="Deudor",
            apellido="UI",
            documento="99992001",
        )
        personas.agregar_rol(deudor_id, "DEUDOR")

        inversor_id = personas.crear(
            nombre="Inversor",
            apellido="UI",
            documento="99992002",
        )
        personas.agregar_rol(inversor_id, "INVERSOR")

    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta))
    return ruta


def _run_app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=10)
    at.run()
    assert not at.exception
    return at


def _go_to_prestamos(at: AppTest) -> AppTest:
    at.segmented_control(key="pagina").set_value("prestamos")
    at.run()
    assert not at.exception
    assert at.session_state["pagina"] == "prestamos"
    return at


def test_alta_completa_desde_ui_persiste_prestamo_y_queda_en_lista(
    alta_database: Path,
):
    at = _go_to_prestamos(_run_app())

    at.button(key="nuevo_prestamo").click()
    at.run()
    assert not at.exception
    assert at.session_state["prestamo_nuevo_step"] == "form"

    at.number_input(key="alta_capital").set_value(10000.0)
    at.number_input(key="alta_plazo").set_value(3)
    at.number_input(key="alta_tasa").set_value(24.0)
    at.text_input(key="alta_destino").set_value("Prueba UI")
    at.multiselect(key="alta_inversores").select(2)
    at.run()
    assert not at.exception

    assert at.multiselect(key="alta_inversores").value == [2]

    at.button(key="alta_simular").click()
    at.run()
    assert not at.exception
    assert at.session_state["prestamo_nuevo_step"] == "preview"
    assert at.button(key="confirmar_alta").disabled is False

    at.button(key="confirmar_alta").click()
    at.run()
    assert not at.exception
    assert "prestamo_nuevo_step" not in at.session_state

    with BaseDatos(alta_database) as db:
        prestamo = db.consultar_uno(
            """
            SELECT id, numero, estado, capital_original, plazo_meses,
                   sistema, convencion_dias, destino
            FROM prestamos
            ORDER BY id DESC
            LIMIT 1
            """
        )
        assert prestamo is not None
        assert prestamo["estado"] == "ACTIVO"
        assert Decimal(str(prestamo["capital_original"])) == Decimal("10000.00")
        assert prestamo["plazo_meses"] == 3
        assert prestamo["destino"] == "Prueba UI"

        version = db.consultar_uno(
            """
            SELECT tasa_anual, modalidad_tasa
            FROM versiones_tasa
            WHERE prestamo_id = ?
            ORDER BY version DESC
            LIMIT 1
            """,
            (prestamo["id"],),
        )
        assert version is not None
        assert Decimal(str(version["tasa_anual"])) == Decimal("0.24")
        assert version["modalidad_tasa"] == "TNA"

        cuotas = db.consultar_uno(
            "SELECT COUNT(*) AS n FROM cuotas WHERE version_id = "
            "(SELECT id FROM versiones_tasa WHERE prestamo_id = ? ORDER BY version DESC LIMIT 1)",
            (prestamo["id"],),
        )
        assert cuotas["n"] == 3

        participacion = db.consultar_uno(
            """
            SELECT porcentaje, capital_aportado
            FROM participaciones
            WHERE prestamo_id = ? AND inversor_id = 2
            """,
            (prestamo["id"],),
        )
        assert participacion is not None
        assert Decimal(str(participacion["porcentaje"])) == Decimal("1")
        assert Decimal(str(participacion["capital_aportado"])) == Decimal("10000.00")

        desembolso = db.consultar_uno(
            """
            SELECT COUNT(*) AS n
            FROM ledger
            WHERE entidad = 'PRESTAMO'
              AND entidad_id = ?
              AND tipo_movimiento = 'DESEMBOLSO'
            """,
            (prestamo["id"],),
        )
        assert desembolso["n"] == 1

        audit = db.consultar_uno(
            """
            SELECT COUNT(*) AS n
            FROM auditoria
            WHERE entidad = 'PRESTAMO'
              AND entidad_id = ?
              AND operacion IN ('PRESTAMO_CREADO', 'PRESTAMO_ACTIVADO')
            """,
            (prestamo["id"],),
        )
        assert audit["n"] == 2

        assert db.verificar_integridad_completa() is True

    assert any(
        "Préstamo #" in str(element.value)
        for element in at.markdown
    ) or any(
        "Préstamo #" in str(element.value)
        for element in at.title + at.header + at.subheader
    )


def test_alta_sin_inversor_no_habilita_confirmacion(
    alta_database: Path,
):
    at = _go_to_prestamos(_run_app())

    at.button(key="nuevo_prestamo").click()
    at.run()
    assert not at.exception

    at.button(key="alta_simular").click()
    at.run()
    assert not at.exception
    assert at.button(key="confirmar_alta").disabled is True

    with BaseDatos(alta_database) as db:
        assert db.consultar_uno(
            "SELECT COUNT(*) AS n FROM prestamos"
        )["n"] == 0


def test_alta_ui_no_escribe_sqlite_directamente():
    path = (
        Path(__file__).resolve().parents[1]
        / "ui"
        / "pagina_alta_prestamo.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imports_sqlite = [
        node
        for node in tree.body
        if isinstance(node, ast.Import)
        and any(alias.name == "sqlite3" for alias in node.names)
    ]
    assert imports_sqlite == []

    assert ".ejecutar(" not in source
    assert "INSERT INTO" not in source
    assert "UPDATE " not in source
    assert "DELETE FROM" not in source



def test_la_simulacion_financiera_del_alta_vive_fuera_de_la_ui():
    path = (
        Path(__file__).resolve().parents[1]
        / "ui"
        / "pagina_alta_prestamo.py"
    )
    source = path.read_text(encoding="utf-8")

    tree = ast.parse(source)
    imports = [
        alias.name
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    ]
    from_imports = [
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    ]

    assert "sqlite3" not in imports
    assert all("generar_tabla" not in (module or "") for module in from_imports)
    assert "from dominio import" in source
    assert "interes_periodo(" not in source

    assert "ServicioSimulacionPrestamo" in source
    assert "simulador.generar_tabla(" in source
