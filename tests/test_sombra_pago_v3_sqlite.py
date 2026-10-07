"""I2 integration tests: real SQLite SOMBRA keeps Legacy effective."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.fabrica_sombra_pago_v3_sqlite import (
    crear_puente_sombra_pago_v3_sqlite,
)
from aplicacion.servicios.pagos import ServicioPagos
from aplicacion.servicios.sombra_pago_v3_sqlite import SombraPagoV3SQLite
from aplicacion.servicios.puente_motor_pago_v3 import (
    ModoMotorPagoV3,
    PuenteMotorPagoV3,
)
from dominio.excepciones import ErrorInvariante
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo
from infraestructura.repositorios.registro_pago_v3 import (
    RepositorioRegistroPagoSQLiteV3,
)
from aplicacion.servicios import ServicioPrestamos


def _crear_prestamo(db: BaseDatos) -> int:
    personas = PersonaRepo(db)
    deudor_id = personas.crear(nombre="Deudor", apellido="I2")
    inversor_id = personas.crear(nombre="Inversor", apellido="I2")
    return ServicioPrestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=Decimal("1000000"),
        plazo_meses=12,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[{"persona_id": inversor_id, "monto": Decimal("1000000")}],
        usuario="i2",
        destino="SOMBRA SQLite",
    )


def _command(db: BaseDatos, prestamo_id: int) -> RegistrarPagoCommand:
    deuda = ServicioPagos(db).calcular_deuda_proximo_pago(
        prestamo_id=prestamo_id,
        fecha_calculo=date(2026, 2, 1),
    )
    assert deuda is not None
    return RegistrarPagoCommand(
        prestamo_id=prestamo_id,
        monto=deuda["total_a_pagar"],
        fecha_real=date(2026, 2, 1),
        fecha_valor=date(2026, 2, 1),
        usuario="i2",
        idempotency_key="I2-SOMBRA-001",
    )


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "i2.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        prestamo_id = _crear_prestamo(db)
        yield db, prestamo_id


def test_i2_sombra_sqlite_legacy_sigue_siendo_efectivo_y_v3_no_persiste(
    db,
):
    base, prestamo_id = db
    command = _command(base, prestamo_id)

    puente = crear_puente_sombra_pago_v3_sqlite(base)
    resultado = puente.ejecutar(command)

    assert resultado.modo is ModoMotorPagoV3.SOMBRA
    assert resultado.error_sombra is None
    assert resultado.divergencia is None
    assert isinstance(resultado.resultado_efectivo, int)
    assert resultado.plan_sombra_v3 is not None
    assert resultado.plan_sombra_v3.revision_prestamo == 0

    revision = base.consultar_uno(
        "SELECT revision_prestamo FROM prestamos WHERE id = ?",
        (prestamo_id,),
    )["revision_prestamo"]
    assert revision == 1

    assert base.consultar_uno(
        "SELECT COUNT(*) AS n FROM pagos WHERE prestamo_id = ?",
        (prestamo_id,),
    )["n"] == 1
    assert base.consultar_uno(
        "SELECT COUNT(*) AS n FROM pagos WHERE prestamo_id = ? AND motor_version LIKE 'V3%'",
        (prestamo_id,),
    )["n"] == 0

    assert base.consultar_uno(
        "SELECT COUNT(*) AS n FROM devengamientos WHERE prestamo_id = ?",
        (prestamo_id,),
    )["n"] == 0


def test_i2_el_plan_sombra_no_relee_estado_despues_de_legacy(db):
    base, prestamo_id = db
    command = _command(base, prestamo_id)

    repo = RepositorioRegistroPagoSQLiteV3(base)
    sombra = SombraPagoV3SQLite(repo)

    original = repo.obtener_estado_pago
    snapshots = []

    def capturar(command_):
        snapshot = original(command_)
        snapshots.append(snapshot)
        return snapshot

    sombra.capturar_snapshot = capturar

    def legacy(command_):
        return ServicioPagos(base).registrar_pago(
            prestamo_id=command_.prestamo_id,
            monto=command_.monto,
            fecha_real=command_.fecha_real,
            usuario=command_.usuario,
        )

    puente = PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.SOMBRA,
        registrar_legacy=legacy,
        capturar_snapshot=sombra.capturar_snapshot,
        planificar_v3_sombra=sombra.planificar,
        comparar_sombra=lambda pago_id, plan: None,
    )
    resultado = puente.ejecutar(command)

    assert len(snapshots) == 1
    assert snapshots[0].revision_prestamo == 0
    assert resultado.plan_sombra_v3.revision_prestamo == 0

    revision_actual = base.consultar_uno(
        "SELECT revision_prestamo FROM prestamos WHERE id = ?",
        (prestamo_id,),
    )["revision_prestamo"]
    assert revision_actual == 1


def test_i2_error_del_calculo_v3_es_no_bloqueante_en_sqlite(db):
    base, prestamo_id = db
    command = _command(base, prestamo_id)

    repo = RepositorioRegistroPagoSQLiteV3(base)
    sombra = SombraPagoV3SQLite(
        repo,
        calculador_plan=lambda **kwargs: (_ for _ in ()).throw(
            ErrorInvariante("fallo V3 sombra I2")
        ),
    )

    legacy = ServicioPagos(base)

    puente = PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.SOMBRA,
        registrar_legacy=lambda c: legacy.registrar_pago(
            prestamo_id=c.prestamo_id,
            monto=c.monto,
            fecha_real=c.fecha_real,
            usuario=c.usuario,
        ),
        capturar_snapshot=sombra.capturar_snapshot,
        planificar_v3_sombra=sombra.planificar,
        comparar_sombra=lambda *_: None,
    )

    resultado = puente.ejecutar(command)

    assert isinstance(resultado.resultado_efectivo, int)
    assert resultado.plan_sombra_v3 is None
    assert resultado.error_sombra == "ErrorInvariante: fallo V3 sombra I2"
    assert base.consultar_uno(
        "SELECT COUNT(*) AS n FROM pagos WHERE prestamo_id = ?",
        (prestamo_id,),
    )["n"] == 1
