"""I8: drill real de V3 -> Legacy sobre un préstamo SQLite."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios import ServicioPagos, ServicioPrestamos
from aplicacion.servicios.drill_rollback_motor_pago_v3 import (
    DrillRollbackMotorPagoV3,
)
from aplicacion.servicios.fabrica_registro_pago_v3 import (
    crear_registrador_pago_v3_completo,
)
from aplicacion.servicios.puente_motor_pago_v3 import (
    ModoMotorPagoV3,
    PuenteMotorPagoV3,
)
from aplicacion.servicios.preflight_motor_pago_v3 import (
    CriterioPreflightV3,
    ResultadoPreflightV3,
)
from dominio.tipos import ConvencionDias, ModalidadTasa
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "i8.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor = personas.crear(nombre="Deudor", apellido="I8")
        inversor = personas.crear(nombre="Inversor", apellido="I8")
        prestamo_id = ServicioPrestamos(db).crear_completo(
            deudor_id=deudor,
            capital=Decimal("1000000"),
            plazo_meses=12,
            tasa_anual=Decimal("0.30"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 1, 1),
            inversores=[
                {"persona_id": inversor, "monto": Decimal("1000000")}
            ],
            usuario="i8",
            destino="Drill rollback",
        )
        yield db, prestamo_id


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
        usuario="i8",
        idempotency_key=key,
    )


def test_i8_v3_y_luego_legacy_posterior_continuan_sobre_el_mismo_prestamo(db):
    base, prestamo_id = db

    preflight = ResultadoPreflightV3(
        apto=True,
        criterios=(
            CriterioPreflightV3("drill_controlado", True, "OK"),
        ),
    )

    command_v3 = _comando(
        base, prestamo_id, date(2026, 2, 1), "I8-V3"
    )

    def crear_puente(modo):
        if modo is ModoMotorPagoV3.V3:
            servicio_v3 = crear_registrador_pago_v3_completo(
                base,
                tasa_anual=Decimal("0.30"),
                modalidad_tasa=ModalidadTasa.TNA,
                convencion_dias=ConvencionDias.ACTUAL_365,
            )
            return PuenteMotorPagoV3(
                modo=modo,
                registrar_v3=servicio_v3.ejecutar,
            )

        servicio_legacy = ServicioPagos(base)
        return PuenteMotorPagoV3(
            modo=modo,
            registrar_legacy=lambda c: servicio_legacy.registrar_pago(
                prestamo_id=c.prestamo_id,
                monto=c.monto,
                fecha_real=c.fecha_real,
                usuario=c.usuario,
                medio=c.medio,
                referencia=c.referencia,
                nota=c.nota,
                opcion_adelanto=c.opcion_adelanto,
            ),
        )

    drill = DrillRollbackMotorPagoV3(
        crear_puente=crear_puente,
    )
    resultado = drill.ejecutar(
        command_v3=command_v3,
        construir_command_legacy=lambda: _comando(
            base, prestamo_id, date(2026, 3, 1), "I8-LEGACY"
        ),
        preflight=preflight,
    )

    assert resultado.decision_v3.modo is ModoMotorPagoV3.V3
    assert resultado.decision_legacy.modo is ModoMotorPagoV3.LEGACY
    assert resultado.resultado_v3.resultado_efectivo.pago_id > 0
    assert resultado.resultado_legacy.resultado_efectivo > 0

    pagos = base.consultar(
        """SELECT motor_version
           FROM pagos
           WHERE prestamo_id = ?
           ORDER BY id""",
        (prestamo_id,),
    )
    assert len(pagos) == 2
    assert str(pagos[0]["motor_version"]).startswith("V3-")
    assert str(pagos[1]["motor_version"]) in {"LEGACY", "LEGACY-SIMULACION"}


def test_i8_no_hace_fallback_automatico_si_v3_falla():
    ejecuciones = []

    def crear_puente(modo):
        if modo is ModoMotorPagoV3.V3:
            return PuenteMotorPagoV3(
                modo=modo,
                registrar_v3=lambda _: (_ for _ in ()).throw(
                    RuntimeError("fallo V3 controlado")
                ),
            )
        return PuenteMotorPagoV3(
            modo=modo,
            registrar_legacy=lambda _: ejecuciones.append("legacy") or "ok",
        )

    drill = DrillRollbackMotorPagoV3(crear_puente=crear_puente)

    with pytest.raises(RuntimeError, match="fallo V3 controlado"):
        drill.ejecutar(
            command_v3=object(),
            construir_command_legacy=lambda: object(),
            preflight=ResultadoPreflightV3(
                apto=True,
                criterios=(),
            ),
        )

    assert ejecuciones == []
