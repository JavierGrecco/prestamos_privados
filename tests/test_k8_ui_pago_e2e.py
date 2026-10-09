"""Aceptación de registro de pago real desde la UI.

El recorrido usa AppTest sobre ui/app.py y luego inspecciona la misma SQLite
para demostrar que la confirmación pasó por la frontera de aplicación y dejó
la operación completa.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
import ast

import pytest
from streamlit.testing.v1 import AppTest

from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo
from tests.ui_auth_helpers import iniciar_apptest_autenticado


APP = Path(__file__).resolve().parents[1] / "ui" / "app.py"


@pytest.fixture
def pago_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ruta = tmp_path / "pago-ui.db"

    inicio = date.today().replace(day=1)

    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)

        deudor_id = personas.crear(
            nombre="Deudor",
            apellido="UI",
            documento="99991001",
        )
        personas.agregar_rol(deudor_id, "DEUDOR")

        inversor_id = personas.crear(
            nombre="Inversor",
            apellido="UI",
            documento="99991002",
        )
        personas.agregar_rol(inversor_id, "INVERSOR")

        ServicioPrestamos(db).crear_completo(
            deudor_id=deudor_id,
            capital=Decimal("1000.00"),
            plazo_meses=3,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=inicio,
            inversores=[
                {"persona_id": inversor_id, "monto": Decimal("1000.00")},
            ],
            usuario="ui-test",
            tc_inicial=Decimal("1500.00"),
            destino="Pago end-to-end",
        )

    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta))
    return ruta


def _run_app() -> AppTest:
    from os import environ
    ruta = Path(environ["PRESTAMOS_DB_PATH"])
    at = AppTest.from_file(APP, default_timeout=10)
    return iniciar_apptest_autenticado(at, ruta)


def _go_to(at: AppTest, pagina: str) -> AppTest:
    at.button(key=f"nav_{pagina}").click()
    at.run()
    assert not at.exception
    assert at.session_state["pagina"] == pagina
    return at


def test_pago_sombra_se_registra_desde_la_ui_y_deja_evidencia(
    pago_database: Path,
):
    at = _go_to(_run_app(), "prestamos")

    at.button(key="ver_prestamo_1").click()
    at.run()
    assert not at.exception
    assert at.session_state["prestamo_seleccionado"] == 1

    at.button(key="ir_registrar_pago").click()
    at.run()
    assert not at.exception

    assert at.segmented_control(key="motor_pago_modo_solicitado").value == "SOMBRA"
    assert at.date_input(key="pago_fecha").value is not None
    assert at.date_input(key="pago_fecha_valor").value is not None
    assert at.date_input(key="pago_fecha_valor").value == at.date_input(
        key="pago_fecha"
    ).value

    monto = at.number_input(key="pago_monto").value
    assert monto > 0

    at.button(key="confirmar_pago").click()
    at.run()
    assert not at.exception

    with BaseDatos(pago_database) as db:
        pago = db.consultar_uno(
            """
            SELECT id, monto_moneda_pago, tipo_pago, motor_version,
                   idempotency_key, plan_hash, plan_json
            FROM pagos
            WHERE prestamo_id = 1
            ORDER BY id DESC
            LIMIT 1
            """
        )
        assert pago is not None
        assert Decimal(str(pago["monto_moneda_pago"])) == Decimal(str(monto))
        assert pago["motor_version"] == "LEGACY"
        assert pago["id"] > 0

        total_imputado = db.consultar_uno(
            "SELECT COALESCE(SUM(CAST(monto AS REAL)), 0) total FROM imputaciones WHERE pago_id = ?",
            (pago["id"],),
        )
        assert total_imputado["total"] == pytest.approx(float(monto))

        ledger = db.consultar(
            "SELECT tipo_movimiento, debe, haber FROM ledger WHERE correlacion_id = "
            "(SELECT correlacion_id FROM ledger WHERE entidad='PAGO' AND entidad_id=? LIMIT 1) "
            "ORDER BY id",
            (pago["id"],),
        )
        assert len(ledger) >= 4
        assert any(row["tipo_movimiento"] == "PAGO" for row in ledger)
        assert any(
            row["tipo_movimiento"] == "PAGO_RECIBIDO"
            for row in ledger
        )

        auditoria = db.consultar_uno(
            "SELECT COUNT(*) n FROM auditoria WHERE entidad='PAGO' AND entidad_id=?",
            (pago["id"],),
        )
        assert auditoria["n"] >= 1

        ejecucion = db.consultar_uno(
            """
            SELECT resultado, revision_snapshot
            FROM ejecuciones_sombra_v3
            WHERE pago_legacy_id=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (pago["id"],),
        )
        assert ejecucion is not None
        assert ejecucion["resultado"] in {
            "SIN_DIVERGENCIA",
            "DIVERGENCIA",
            "ERROR_SOMBRA",
        }
        assert ejecucion["revision_snapshot"] >= 0

        observaciones = db.consultar_uno(
            "SELECT COUNT(*) n FROM observaciones_sombra_v3 WHERE pago_legacy_id=?",
            (pago["id"],),
        )
        if ejecucion["resultado"] == "SIN_DIVERGENCIA":
            assert observaciones["n"] == 0
        else:
            assert observaciones["n"] >= 1


def test_preview_parcial_no_contiene_waterfall_ni_tasa_hardcodeados():
    path = (
        Path(__file__).resolve().parents[1]
        / "ui"
        / "pagina_registrar_pago.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    funcion = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_renderizar_preview_parcial"
    )

    llamadas = [
        node.func.id
        for node in ast.walk(funcion)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "min" not in llamadas

    literales = [
        node.value
        for node in ast.walk(funcion)
        if isinstance(node, ast.Constant)
    ]
    assert 0.025 not in literales
    assert "0.025" not in literales


def test_ui_consume_fachada_unica_de_preview():
    path = (
        Path(__file__).resolve().parents[1]
        / "ui"
        / "pagina_registrar_pago.py"
    )
    source = path.read_text(encoding="utf-8")
    assert "ServicioPagosConSimulacion" not in source
    assert "ServicioPreviewPago" in source
    assert "servicio.previsualizar_por_modo(" in source


def test_fachada_preview_selecciona_ruta_por_modo():
    from aplicacion.consultas.preview_pago import ServicioPreviewPago
    from aplicacion.servicios.puente_motor_pago_v3 import ModoMotorPagoV3

    class StubLegacy:
        def simular_pago(self, *args):
            return {"origen": "legacy"}

        def calcular_deuda_proximo_pago(self, *args):
            return None

        def simular_adelanto(self, *args):
            return None

    class StubV3:
        def previsualizar(self, **kwargs):
            return "v3"

    servicio = ServicioPreviewPago.__new__(ServicioPreviewPago)
    servicio._legacy = StubLegacy()
    servicio._v3 = StubV3()

    legacy = servicio.previsualizar_por_modo(
        modo=ModoMotorPagoV3.LEGACY,
        prestamo_id=1,
        monto=1,
        fecha_real=date(2026, 10, 8),
        fecha_valor=date(2026, 10, 8),
    )
    v3 = servicio.previsualizar_por_modo(
        modo=ModoMotorPagoV3.SOMBRA,
        prestamo_id=1,
        monto=1,
        fecha_real=date(2026, 10, 8),
        fecha_valor=date(2026, 10, 8),
    )

    assert legacy == {"origen": "legacy"}
    assert v3 == "v3"
