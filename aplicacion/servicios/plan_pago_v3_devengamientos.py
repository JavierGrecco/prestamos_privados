"""Composición G2: snapshot + devengamientos + PlanPago, sin efectos secundarios."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping

from dominio.excepciones import ErrorInvariante
from dominio.motor_pagos_v3 import Devengamiento, PlanPago, ObligacionSnapshot, calcular_plan_pago
from dominio.politica_devengamiento_v3 import (
    PoliticaInteresCapitalPendiente,
    generar_interes_capital_pendiente,
)
from aplicacion.servicios.registro_pago_v3 import EstadoRegistroPagoV3


@dataclass(frozen=True)
class ResultadoPlanPagoV3Devengamientos:
    """Plan financiero y eventos nuevos calculados para esa fecha."""

    plan: PlanPago
    devengamientos_nuevos: Mapping[int, tuple[Devengamiento, ...]]

    def __post_init__(self) -> None:
        normalizado = {
            int(cuota_id): tuple(eventos)
            for cuota_id, eventos in self.devengamientos_nuevos.items()
        }
        object.__setattr__(self, "devengamientos_nuevos", normalizado)



def calcular_plan_pago_con_devengamientos(
    *,
    estado: EstadoRegistroPagoV3,
    fecha_valor: date,
    monto_recibido: Decimal,
    politica_interes_capital: PoliticaInteresCapitalPendiente | None = None,
    ultimo_hasta_por_cuota: Mapping[int, date | None] | None = None,
) -> ResultadoPlanPagoV3Devengamientos:
    """Construye el mismo PlanPago V3 incorporando eventos nuevos explícitos."""
    if estado.prestamo_id <= 0:
        raise ErrorInvariante("El estado de registro debe identificar un préstamo válido")

    eventos = {}
    if politica_interes_capital is not None:
        eventos = generar_interes_capital_pendiente(
            obligaciones=tuple(estado.obligaciones),
            fecha_valor=fecha_valor,
            politica=politica_interes_capital,
            ultimo_hasta_por_cuota=ultimo_hasta_por_cuota,
        )

    plan = calcular_plan_pago(
        prestamo_id=estado.prestamo_id,
        fecha_valor=fecha_valor,
        revision_prestamo=estado.revision_prestamo,
        monto_recibido=monto_recibido,
        obligaciones=tuple(estado.obligaciones),
        devengamientos_por_cuota=eventos,
    )
    plan.validar()
    return ResultadoPlanPagoV3Devengamientos(
        plan=plan,
        devengamientos_nuevos=eventos,
    )
