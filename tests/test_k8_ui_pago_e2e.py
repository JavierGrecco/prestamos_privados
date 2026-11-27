"""Aceptación de registro de pago real desde la UI.

El recorrido usa AppTest sobre ui/app.py y luego inspecciona la misma SQLite
para demostrar que la confirmación pasó por la frontera de aplicación y dejó
la operación completa.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Barrier, local
import ast

import pytest
from streamlit.runtime.scriptrunner import ScriptRunner
from streamlit.testing.v1 import AppTest

from infraestructura.composicion.prestamos import crear_servicio_prestamos
from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import LedgerRepo, PersonaRepo
from infraestructura.repositorios.auditoria import AuditoriaRepo
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

        crear_servicio_prestamos(db).crear_completo(
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

    fecha_valor_distinta = at.date_input(key="pago_fecha_valor").value + timedelta(days=1)
    at.date_input(key="pago_fecha_valor").set_value(fecha_valor_distinta)
    at.run()
    assert not at.exception

    monto = at.number_input(key="pago_monto").value
    assert monto > 0

    at.button(key="confirmar_pago").click()
    at.run()
    assert not at.exception

    with BaseDatos(pago_database) as db:
        pago = db.consultar_uno(
            """
            SELECT id, fecha_valor, monto_moneda_pago, tipo_pago, motor_version,
                   idempotency_key, idempotency_fingerprint, plan_hash, plan_json
            FROM pagos
            WHERE prestamo_id = 1
            ORDER BY id DESC
            LIMIT 1
            """
        )
        assert pago is not None
        assert str(pago["fecha_valor"]) == fecha_valor_distinta.isoformat()
        assert Decimal(str(pago["monto_moneda_pago"])) == Decimal(str(monto))
        assert pago["motor_version"] == "LEGACY"
        assert pago["id"] > 0
        assert pago["idempotency_key"]
        assert len(pago["idempotency_fingerprint"]) == 64

        imputaciones = db.consultar(
            "SELECT monto FROM imputaciones WHERE pago_id = ? ORDER BY id",
            (pago["id"],),
        )
        total_imputado = sum(
            (Decimal(str(fila["monto"])) for fila in imputaciones),
            Decimal("0.00"),
        )
        assert total_imputado == Decimal(str(pago["monto_moneda_pago"]))

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


def test_dos_sesiones_ui_confirman_en_paralelo_el_mismo_pago_sin_duplicarlo(
    pago_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dos sesiones reales del entrypoint reintentan la misma intención de pago."""
    contexto_sesion = local()
    sesiones_por_objeto: dict[int, str] = {}
    ejecutar_apptest = AppTest.run
    inicializar_script_runner = ScriptRunner.__init__

    def ejecutar_con_sesion_estable(self, *args, **kwargs):
        # AppTest crea otro ScriptRunner en cada rerun. El identificador debe
        # pertenecer al objeto AppTest, no a cada instancia transitoria.
        session_id = sesiones_por_objeto.setdefault(
            id(self),
            f"pago-ui-concurrente-{len(sesiones_por_objeto) + 1}",
        )
        anterior = getattr(contexto_sesion, "session_id", None)
        contexto_sesion.session_id = session_id
        try:
            return ejecutar_apptest(self, *args, **kwargs)
        finally:
            if anterior is None:
                del contexto_sesion.session_id
            else:
                contexto_sesion.session_id = anterior

    def inicializar_con_id_unico(self, *args, **kwargs):
        if kwargs.get("session_id") == "test session id":
            session_id = getattr(contexto_sesion, "session_id", None)
            if session_id is not None:
                kwargs["session_id"] = session_id
        inicializar_script_runner(self, *args, **kwargs)

    # AppTest reutiliza por defecto el mismo session_id fijo. Asignamos uno
    # estable por objeto para que su cache_resource scope="session" sobreviva
    # todos los reruns y sea distinto para cada ventana simulada.
    monkeypatch.setattr(AppTest, "run", ejecutar_con_sesion_estable)
    monkeypatch.setattr(ScriptRunner, "__init__", inicializar_con_id_unico)

    sesiones = [_run_app(), _run_app()]
    for at in sesiones:
        _go_to(at, "prestamos")
        at.button(key="ver_prestamo_1").click()
        at.run()
        assert not at.exception
        assert at.session_state["prestamo_seleccionado"] == 1

        at.button(key="ir_registrar_pago").click()
        at.run()
        assert not at.exception
        assert at.segmented_control(
            key="motor_pago_modo_solicitado"
        ).value == "SOMBRA"

    monto_a = Decimal(str(sesiones[0].number_input(key="pago_monto").value))
    monto_b = Decimal(str(sesiones[1].number_input(key="pago_monto").value))
    assert monto_a > 0
    assert monto_a == monto_b
    assert sesiones[0].date_input(key="pago_fecha").value == sesiones[1].date_input(
        key="pago_fecha"
    ).value
    assert sesiones[0].date_input(
        key="pago_fecha_valor"
    ).value == sesiones[1].date_input(key="pago_fecha_valor").value
    assert sesiones[0].selectbox(key="pago_medio").value == sesiones[1].selectbox(
        key="pago_medio"
    ).value
    assert sesiones[0].text_input(key="pago_nota").value == sesiones[1].text_input(
        key="pago_nota"
    ).value

    clave = "test-ui-concurrente-mismo-pago"
    for at in sesiones:
        # La clave de negocio debe ser la misma: así el segundo submit es un
        # retry de la misma intención, no un segundo pago independiente.
        at.session_state["pago_idempotency_key"] = clave

    inicio = Barrier(2, timeout=10)

    def confirmar(at: AppTest) -> None:
        inicio.wait()
        at.button(key="confirmar_pago").click()
        at.run()
        assert not at.exception

    with ThreadPoolExecutor(max_workers=2) as pool:
        futuros = [pool.submit(confirmar, at) for at in sesiones]
        for futuro in futuros:
            futuro.result(timeout=45)

    # Las dos sesiones deben completar su recorrido y consumir la clave local,
    # tanto si una creó el pago como si recibió el resultado idempotente.
    for at in sesiones:
        assert "pago_idempotency_key" not in at.session_state

    with BaseDatos(pago_database) as db:
        pagos = db.consultar(
            """
            SELECT id, monto_moneda_pago, motor_version,
                   idempotency_key, idempotency_fingerprint
            FROM pagos
            WHERE prestamo_id = 1
            ORDER BY id
            """
        )
        assert len(pagos) == 1
        pago = pagos[0]
        pago_id = int(pago["id"])
        assert Decimal(str(pago["monto_moneda_pago"])) == monto_a
        assert pago["motor_version"] == "LEGACY"
        assert pago["idempotency_key"] == clave
        assert len(pago["idempotency_fingerprint"]) == 64

        imputaciones = db.consultar(
            "SELECT monto FROM imputaciones WHERE pago_id = ? ORDER BY id",
            (pago_id,),
        )
        total_imputado = sum(
            (Decimal(str(fila["monto"])) for fila in imputaciones),
            Decimal("0.00"),
        )
        assert imputaciones
        assert total_imputado == monto_a

        correlacion = db.consultar_uno(
            """
            SELECT correlacion_id
            FROM ledger
            WHERE entidad = 'PAGO' AND entidad_id = ?
            LIMIT 1
            """,
            (pago_id,),
        )
        assert correlacion is not None
        movimientos = db.consultar(
            "SELECT tipo_movimiento FROM ledger WHERE correlacion_id = ?",
            (correlacion["correlacion_id"],),
        )
        assert len(movimientos) >= 4
        assert any(x["tipo_movimiento"] == "PAGO" for x in movimientos)
        assert any(x["tipo_movimiento"] == "PAGO_RECIBIDO" for x in movimientos)
        assert LedgerRepo(db).verificar_cuadre() is True

        auditoria = db.consultar_uno(
            "SELECT COUNT(*) AS cantidad FROM auditoria "
            "WHERE entidad = 'PAGO' AND entidad_id = ?",
            (pago_id,),
        )
        assert auditoria["cantidad"] == 1

        ejecuciones_sombra = db.consultar_uno(
            "SELECT COUNT(*) AS cantidad FROM ejecuciones_sombra_v3 "
            "WHERE pago_legacy_id = ?",
            (pago_id,),
        )
        # El retry idempotente debe resolverse antes de ejecutar otro snapshot
        # o escribir una segunda observación SOMBRA.
        assert ejecuciones_sombra["cantidad"] == 1


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


def _snapshot_financiero(db_path: Path) -> dict[str, tuple[tuple, ...]]:
    """Snapshot de todas las tablas persistentes salvo estado de sesión/autenticación."""
    excluir = {
        "sesiones",
        "sesiones_usuario",
        "sesiones_autenticacion",
        "tokens_recuperacion",
    }
    with BaseDatos(db_path) as db:
        tablas = db.consultar(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
        snapshot: dict[str, tuple[tuple, ...]] = {}
        for fila in tablas:
            tabla = str(fila["name"])
            if tabla in excluir:
                continue
            filas = db.consultar(f'SELECT * FROM "{tabla}" ORDER BY rowid')
            snapshot[tabla] = tuple(tuple(registro) for registro in filas)
        return snapshot


def _preparar_sesiones_independientes(
    pago_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> list[AppTest]:
    """Crea dos AppTest con IDs de sesión estables y conexiones aisladas."""
    contexto_sesion = local()
    sesiones_por_objeto: dict[int, str] = {}
    ejecutar_apptest = AppTest.run
    inicializar_script_runner = ScriptRunner.__init__

    def ejecutar_con_sesion_estable(self, *args, **kwargs):
        session_id = sesiones_por_objeto.setdefault(
            id(self),
            f"pago-ui-revision-{len(sesiones_por_objeto) + 1}",
        )
        anterior = getattr(contexto_sesion, "session_id", None)
        contexto_sesion.session_id = session_id
        try:
            return ejecutar_apptest(self, *args, **kwargs)
        finally:
            if anterior is None:
                del contexto_sesion.session_id
            else:
                contexto_sesion.session_id = anterior

    def inicializar_con_id_unico(self, *args, **kwargs):
        if kwargs.get("session_id") == "test session id":
            session_id = getattr(contexto_sesion, "session_id", None)
            if session_id is not None:
                kwargs["session_id"] = session_id
        inicializar_script_runner(self, *args, **kwargs)

    monkeypatch.setattr(AppTest, "run", ejecutar_con_sesion_estable)
    monkeypatch.setattr(ScriptRunner, "__init__", inicializar_con_id_unico)

    sesiones = [_run_app(), _run_app()]
    for at in sesiones:
        _go_to(at, "prestamos")
        at.button(key="ver_prestamo_1").click()
        at.run()
        assert not at.exception
        at.button(key="ir_registrar_pago").click()
        at.run()
        assert not at.exception
        assert at.segmented_control(
            key="motor_pago_modo_solicitado"
        ).value == "SOMBRA"
    return sesiones


def test_dos_sesiones_ui_bloquean_confirmacion_con_revision_obsoleta(
    pago_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sesiones = _preparar_sesiones_independientes(pago_database, monkeypatch)
    revision_inicial = sesiones[0].session_state["pago_revision_preview"]
    assert sesiones[1].session_state["pago_revision_preview"] == revision_inicial

    # Son dos intenciones distintas, no un reintento de la misma clave.
    sesiones[0].session_state["pago_idempotency_key"] = "ui-intencion-distinta-a"
    sesiones[1].session_state["pago_idempotency_key"] = "ui-intencion-distinta-b"

    sesiones[0].button(key="confirmar_pago").click()
    sesiones[0].run()
    assert not sesiones[0].exception

    with BaseDatos(pago_database) as db:
        revision_actual = db.consultar_uno(
            "SELECT revision_prestamo FROM prestamos WHERE id = 1"
        )["revision_prestamo"]
        cantidad_pagos = db.consultar_uno(
            "SELECT COUNT(*) AS n FROM pagos WHERE prestamo_id = 1"
        )["n"]
    assert revision_actual == revision_inicial + 1
    assert cantidad_pagos == 1

    # El segundo preview permanece vinculado a la revisión anterior. El rerun
    # detecta el cambio, descarta la confirmación pendiente y pide revisar
    # explícitamente el nuevo cálculo antes de habilitar otro pago.
    sesiones[1].button(key="confirmar_pago").click()
    sesiones[1].run()
    assert not sesiones[1].exception
    assert sesiones[1].session_state["pago_revision_preview"] == revision_inicial
    assert "actualizar_preview_pago" in {
        button.key for button in sesiones[1].button
    }

    with BaseDatos(pago_database) as db:
        assert db.consultar_uno(
            "SELECT COUNT(*) AS n FROM pagos WHERE prestamo_id = 1"
        )["n"] == 1
        assert LedgerRepo(db).verificar_cuadre() is True


def test_fallo_inyectado_despues_de_auditoria_revierte_todo_el_pago_ui(
    pago_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    at = _go_to(_run_app(), "prestamos")
    at.button(key="ver_prestamo_1").click()
    at.run()
    at.button(key="ir_registrar_pago").click()
    at.run()
    assert not at.exception

    antes = _snapshot_financiero(pago_database)
    registrar_original = AuditoriaRepo.registrar

    def registrar_y_fallar(self, **kwargs):
        registrar_original(self, **kwargs)
        raise RuntimeError("fallo inyectado después de escribir auditoría")

    monkeypatch.setattr(AuditoriaRepo, "registrar", registrar_y_fallar)
    at.button(key="confirmar_pago").click()
    at.run()

    assert not at.exception
    assert at.session_state.get("pago_idempotency_key")
    assert _snapshot_financiero(pago_database) == antes

    with BaseDatos(pago_database) as db:
        assert db.consultar_uno(
            "SELECT COUNT(*) AS n FROM pagos WHERE prestamo_id = 1"
        )["n"] == 0
        assert db.consultar_uno(
            "SELECT COUNT(*) AS n FROM auditoria WHERE entidad = 'PAGO'"
        )["n"] == 0
        assert LedgerRepo(db).verificar_cuadre() is True
