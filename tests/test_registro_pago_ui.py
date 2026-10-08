"""Pruebas de la frontera de pagos consumida por la UI."""

from datetime import date
from decimal import Decimal

import pytest

from aplicacion.servicios.puente_motor_pago_v3 import ModoMotorPagoV3
from aplicacion.servicios.preflight_motor_pago_v3 import (
    CriterioPreflightV3,
    ResultadoPreflightV3,
)
from aplicacion.servicios.registro_pago_ui import ServicioRegistroPagoUI
from dominio.excepciones import ErrorValidacion


class DBStub:
    pass


def _preflight(apto: bool) -> ResultadoPreflightV3:
    return ResultadoPreflightV3(
        apto=apto,
        criterios=(
            CriterioPreflightV3(
                nombre="test",
                cumplido=apto,
                detalle="prueba",
            ),
        ),
    )


def test_resolver_modo_sin_configuracion_conserva_legacy():
    servicio = ServicioRegistroPagoUI(DBStub())

    estado = servicio.resolver_modo(None)

    assert estado.decision.modo is ModoMotorPagoV3.LEGACY
    assert estado.preflight is None


def test_resolver_modo_sombra_no_requiere_preflight():
    servicio = ServicioRegistroPagoUI(DBStub())

    estado = servicio.resolver_modo(ModoMotorPagoV3.SOMBRA)

    assert estado.decision.modo is ModoMotorPagoV3.SOMBRA
    assert estado.preflight is None


def test_v3_exige_preflight_aprobado():
    servicio = ServicioRegistroPagoUI(DBStub())
    servicio.modo_actual = lambda: ModoMotorPagoV3.V3

    with pytest.raises(ErrorValidacion, match="preflight"):
        servicio.registrar(
            command=None,
            modo=ModoMotorPagoV3.V3,
            preflight=_preflight(False),
        )


def test_v3_sin_preflight_tambien_es_rechazado():
    servicio = ServicioRegistroPagoUI(DBStub())
    servicio.modo_actual = lambda: ModoMotorPagoV3.V3

    with pytest.raises(ErrorValidacion, match="preflight"):
        servicio.registrar(
            command=None,
            modo=ModoMotorPagoV3.V3,
            preflight=None,
        )


def test_crear_command_normaliza_dinero_y_fecha_valor():
    servicio = ServicioRegistroPagoUI(DBStub())

    command = servicio.crear_command(
        prestamo_id=7,
        monto=Decimal("100.005"),
        fecha_real=date(2026, 10, 8),
        usuario=" admin ",
        medio="Transferencia",
        referencia="ref-1",
        nota=" pago ",
        opcion_adelanto="RAI",
        idempotency_key=" key-1 ",
    )

    assert command.monto == Decimal("100.01")
    assert command.fecha_valor == date(2026, 10, 8)
    assert command.usuario == "admin"
    assert command.idempotency_key == "key-1"


def test_pago_rechaza_modo_obsoleto():
    servicio = ServicioRegistroPagoUI(DBStub())
    servicio.modo_actual = lambda: ModoMotorPagoV3.SOMBRA

    with pytest.raises(ErrorValidacion, match="cambió desde la pantalla"):
        servicio.registrar(
            command=None,
            modo=ModoMotorPagoV3.LEGACY,
            preflight=None,
        )


def test_crear_command_conserva_fecha_valor_distinta():
    servicio = ServicioRegistroPagoUI(DBStub())

    command = servicio.crear_command(
        prestamo_id=7,
        monto=Decimal("100.00"),
        fecha_real=date(2026, 10, 8),
        fecha_valor=date(2026, 10, 9),
        usuario="admin",
        medio="Transferencia",
        referencia="ref-2",
        nota=None,
        opcion_adelanto=None,
        idempotency_key="key-2",
    )

    assert command.fecha_real == date(2026, 10, 8)
    assert command.fecha_valor == date(2026, 10, 9)
