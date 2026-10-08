"""Composición G2: snapshot + devengamientos + PlanPago, sin efectos secundarios."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping

from dominio.excepciones import ErrorInvariante
from dominio.motor_pagos_v3 import Devengamiento, PlanPago, ObligacionSnapshot, ORDEN_WATERFALL_V3, calcular_plan_pago
from dominio.politica_pago import PoliticaImputacionPago
from dominio.politica_devengamiento_v3 import (
    PoliticaInteresCapitalPendiente,
    PoliticaMoraContractualV3,
    generar_interes_capital_pendiente,
    generar_mora_contractual,
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
    politica_mora: PoliticaMoraContractualV3 | None = None,
    ultimo_hasta_por_cuota: Mapping[int, date | None] | None = None,
    ultimo_hasta_mora_por_cuota: Mapping[int, date | None] | None = None,
    orden_waterfall=ORDEN_WATERFALL_V3,
    politica_pago: PoliticaImputacionPago | None = None,
) -> ResultadoPlanPagoV3Devengamientos:
    """Construye el mismo PlanPago V3 incorporando eventos nuevos explícitos."""
    if politica_pago is not None:
        orden_waterfall = politica_pago.orden_waterfall
        if not politica_pago.interes_compensatorio_post_vencimiento:
            politica_interes_capital = None

    if estado.prestamo_id <= 0:
        raise ErrorInvariante("El estado de registro debe identificar un préstamo válido")

    obligaciones = tuple(estado.obligaciones)
    eventos_interes = {}
    if politica_interes_capital is not None:
        eventos_interes = generar_interes_capital_pendiente(
            obligaciones=obligaciones,
            fecha_valor=fecha_valor,
            politica=politica_interes_capital,
            ultimo_hasta_por_cuota=ultimo_hasta_por_cuota,
        )

    eventos_mora = {}
    if politica_mora is not None:
        eventos_mora = generar_mora_contractual(
            obligaciones=obligaciones,
            fecha_valor=fecha_valor,
            politica=politica_mora,
            ultimo_hasta_por_cuota=ultimo_hasta_mora_por_cuota,
        )

    eventos = {
        cuota_id: tuple(eventos_interes.get(cuota_id, ()))
        + tuple(eventos_mora.get(cuota_id, ()))
        for cuota_id in set(eventos_interes) | set(eventos_mora)
    }

    plan = calcular_plan_pago(
        prestamo_id=estado.prestamo_id,
        fecha_valor=fecha_valor,
        revision_prestamo=estado.revision_prestamo,
        monto_recibido=monto_recibido,
        obligaciones=obligaciones,
        devengamientos_por_cuota=eventos,
        orden_waterfall=orden_waterfall,
    )
    plan.validar()
    return ResultadoPlanPagoV3Devengamientos(
        plan=plan,
        devengamientos_nuevos=eventos,
    )
