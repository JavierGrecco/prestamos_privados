"""Pruebas puras del planificador de pagos V3 en modo SOMBRA."""

from datetime import date
from decimal import Decimal

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.puertos.registro_pago_v3 import EstadoRegistroPagoV3
from aplicacion.servicios.planificador_sombra_pago_v3 import (
    PlanificadorSombraPagoV3,
)


def comando(prestamo_id: int = 42) -> RegistrarPagoCommand:
    return RegistrarPagoCommand(
        prestamo_id=prestamo_id,
        monto=Decimal("125.50"),
        fecha_real=date(2026, 10, 13),
        fecha_valor=date(2026, 10, 13),
        usuario="tester",
        idempotency_key="TEST-SOMBRA-PORT",
    )


class ConsultaEstadoFalsa:
    """Consulta mínima: registra cada lectura para detectar una relectura accidental."""

    def __init__(self, estado: EstadoRegistroPagoV3) -> None:
        self.estado = estado
        self.lecturas: list[int] = []

    def obtener_estado_pago(self, prestamo_id: int) -> EstadoRegistroPagoV3:
        self.lecturas.append(prestamo_id)
        return self.estado


def test_planificador_lee_una_vez_y_calcula_solo_con_el_snapshot():
    estado = EstadoRegistroPagoV3(
        prestamo_id=42,
        revision_prestamo=7,
        obligaciones=({"obligacion_id": 3, "estado": "PENDIENTE"},),
    )
    consulta = ConsultaEstadoFalsa(estado)
    argumentos_recibidos: list[dict] = []

    def calcular(**kwargs):
        argumentos_recibidos.append(kwargs)
        return kwargs

    planificador = PlanificadorSombraPagoV3(
        consulta,
        calculador_plan=calcular,
    )
    cmd = comando()

    snapshot = planificador.capturar_snapshot(cmd)
    plan = planificador.planificar(cmd, snapshot)

    assert consulta.lecturas == [42]
    assert snapshot is estado
    assert plan["prestamo_id"] == 42
    assert plan["revision_prestamo"] == 7
    assert plan["fecha_valor"] == cmd.fecha_valor
    assert plan["monto_recibido"] == Decimal("125.50")
    assert plan["obligaciones"] == estado.obligaciones
    assert len(argumentos_recibidos) == 1


def test_planificador_rechaza_snapshot_de_otro_prestamo_antes_de_calcular():
    estado = EstadoRegistroPagoV3(
        prestamo_id=99,
        revision_prestamo=1,
        obligaciones=(),
    )
    consulta = ConsultaEstadoFalsa(estado)
    calculos: list[dict] = []
    planificador = PlanificadorSombraPagoV3(
        consulta,
        calculador_plan=lambda **kwargs: calculos.append(kwargs),
    )

    with pytest.raises(
        ValueError,
        match="El snapshot no corresponde al préstamo del comando",
    ):
        planificador.planificar(comando(42), estado)

    assert calculos == []
    assert consulta.lecturas == []


def test_planificador_no_relee_si_se_planifica_repetidamente_el_mismo_snapshot():
    estado = EstadoRegistroPagoV3(
        prestamo_id=42,
        revision_prestamo=8,
        obligaciones=(),
    )
    consulta = ConsultaEstadoFalsa(estado)
    planificador = PlanificadorSombraPagoV3(
        consulta,
        calculador_plan=lambda **kwargs: kwargs["revision_prestamo"],
    )
    cmd = comando()
    snapshot = planificador.capturar_snapshot(cmd)

    assert planificador.planificar(cmd, snapshot) == 8
    assert planificador.planificar(cmd, snapshot) == 8
    assert consulta.lecturas == [42]
