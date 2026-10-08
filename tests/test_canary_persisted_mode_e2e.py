"""Regresión end-to-end del canary usando la frontera real de la UI."""
from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.puente_motor_pago_v3 import ModoMotorPagoV3
from aplicacion.servicios.registro_pago_ui import ServicioRegistroPagoUI
from aplicacion.servicios.pagos import ServicioPagos
from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo
from infraestructura.repositorios.ejecuciones_sombra_v3 import EjecucionesSombraV3Repo
from aplicacion.servicios.puente_motor_pago_v3 import (
    EjecucionSombraMotorPagoV3,
    ResultadoEjecucionSombraV3,
)


def _crear_db(path: Path):
    db = BaseDatos(path)
    db.abrir()
    aplicar_migraciones(db)

    personas = PersonaRepo(db)
    deudor = personas.crear(nombre="Deudor", apellido="Canary E2E")
    inversor = personas.crear(nombre="Inversor", apellido="Canary E2E")

    prestamo_id = ServicioPrestamos(db).crear_completo(
        deudor_id=deudor,
        capital=Decimal("1000000"),
        plazo_meses=12,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[{"persona_id": inversor, "monto": Decimal("1000000")}],
        usuario="canary",
        destino="Canary E2E",
    )

    sombra = EjecucionesSombraV3Repo(db)
    for i in range(100):
        sombra.registrar(
            EjecucionSombraMotorPagoV3(
                fingerprint=f"canary-{i}",
                prestamo_id=prestamo_id,
                pago_legacy_id=None,
                resultado=ResultadoEjecucionSombraV3.SIN_DIVERGENCIA,
                revision_snapshot=0,
                resumen=None,
            )
        )

    return db, prestamo_id


def _comando(db, prestamo_id, fecha, key):
    deuda = ServicioPagos(db).calcular_deuda_proximo_pago(
        prestamo_id=prestamo_id,
        fecha_calculo=fecha,
    )
    assert deuda is not None
    return RegistrarPagoCommand(
        prestamo_id=prestamo_id,
        monto=deuda["total_a_pagar"],
        fecha_real=fecha,
        fecha_valor=fecha,
        usuario="canary",
        idempotency_key=key,
    )


def test_canary_e2e_usa_modo_persistente_y_rollback_entre_operaciones(tmp_path: Path):
    db, prestamo_id = _crear_db(tmp_path / "canary-e2e.db")
    try:
        servicio = ServicioRegistroPagoUI(db)

        assert servicio.modo_actual() is ModoMotorPagoV3.SOMBRA
        preflight = servicio.evaluar_preflight()
        assert preflight.apto is True

        estado_v3 = servicio.cambiar_modo(
            nuevo_modo=ModoMotorPagoV3.V3,
            usuario="canary",
            motivo="Canary E2E controlado",
        )
        assert estado_v3.modo is ModoMotorPagoV3.V3

        command_v3 = _comando(db, prestamo_id, date(2026, 2, 1), "CANARY-E2E-V3")
        resultado_v3 = servicio.registrar(
            command=command_v3,
            modo=ModoMotorPagoV3.V3,
            preflight=preflight,
        )
        assert resultado_v3.modo is ModoMotorPagoV3.V3
        assert resultado_v3.pago_id > 0

        estado_legacy = servicio.cambiar_modo(
            nuevo_modo=ModoMotorPagoV3.LEGACY,
            usuario="canary",
            motivo="Rollback E2E controlado",
        )
        assert estado_legacy.modo is ModoMotorPagoV3.LEGACY

        command_legacy = _comando(db, prestamo_id, date(2026, 3, 1), "CANARY-E2E-LEGACY")
        resultado_legacy = servicio.registrar(
            command=command_legacy,
            modo=ModoMotorPagoV3.LEGACY,
        )
        assert resultado_legacy.modo is ModoMotorPagoV3.LEGACY
        assert resultado_legacy.pago_id > 0

        pagos = db.consultar(
            "SELECT id, motor_version FROM pagos WHERE prestamo_id = ? ORDER BY id",
            (prestamo_id,),
        )
        assert len(pagos) == 2
        assert str(pagos[0]["motor_version"]).startswith("V3-")
        assert str(pagos[1]["motor_version"]) in {"LEGACY", "LEGACY-SIMULACION"}
    finally:
        db.cerrar()
