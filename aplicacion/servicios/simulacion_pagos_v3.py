"""V3-E: adaptador de simulación hacia el Motor de Pagos V3.

Esta pieza NO reemplaza ``simular_pago()`` ni ``registrar_pago()``. Es una
ruta paralela de validación que transforma cuotas materializadas del proyecto
en snapshots del motor V3 y devuelve un PlanPago puro.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable, Protocol, Sequence

from dominio.excepciones import ErrorValidacion
from dominio.motor_pagos_v3 import (
    PlanPago,
    ObligacionSnapshot,
    calcular_plan_pago,
)
from dominio.tipos import money


class CuotaMaterializada(Protocol):
    """Atributos mínimos que V3-E necesita de una cuota existente."""

    id: int
    numero: int
    vencimiento: date
    estado: str
    interes_pendiente: Decimal
    capital_pendiente: Decimal
    mora_pendiente: Decimal
    tuvo_pago_parcial: bool


@dataclass(frozen=True)
class ContextoSimulacionV3:
    prestamo_id: int
    fecha_valor: date
    revision_prestamo: int
    monto_recibido: Decimal

    def __post_init__(self) -> None:
        monto = money(self.monto_recibido)
        if self.prestamo_id <= 0:
            raise ErrorValidacion("El préstamo debe tener un ID positivo")
        if self.revision_prestamo < 0:
            raise ErrorValidacion("La revisión del préstamo no puede ser negativa")
        if monto <= 0:
            raise ErrorValidacion("El monto recibido debe ser mayor a cero")
        object.__setattr__(self, "monto_recibido", monto)


def mapear_cuotas_a_snapshot_v3(
    cuotas: Iterable[CuotaMaterializada],
) -> tuple[ObligacionSnapshot, ...]:
    """Mapea cuotas persistidas a snapshots inmutables del motor V3."""
    snapshots: list[ObligacionSnapshot] = []
    for cuota in cuotas:
        try:
            snapshots.append(
                ObligacionSnapshot.desde_cuota_actual(
                    cuota_id=int(cuota.id),
                    numero_cuota=int(cuota.numero),
                    vencimiento=cuota.vencimiento,
                    estado=str(cuota.estado),
                    tuvo_pago_parcial=bool(cuota.tuvo_pago_parcial),
                    interes_pendiente=cuota.interes_pendiente,
                    capital_pendiente=cuota.capital_pendiente,
                    mora_pendiente=cuota.mora_pendiente,
                )
            )
        except AttributeError as exc:
            raise ErrorValidacion(
                f"La cuota no contiene el atributo requerido: {exc.args[0]}"
            ) from exc

    snapshots.sort(key=lambda s: (s.vencimiento, s.numero_cuota, s.cuota_id))
    return tuple(snapshots)


def simular_plan_pago_v3(
    *,
    contexto: ContextoSimulacionV3,
    obligaciones: Sequence[ObligacionSnapshot],
) -> PlanPago:
    """Calcula un plan V3 sobre el estado materializado recibido.

    Esta fase no inventa devengamientos nuevos. Mora/interest adicional se
    incorporarán cuando el adaptador temporal V3-C/D sea integrado al servicio.
    """
    return calcular_plan_pago(
        prestamo_id=contexto.prestamo_id,
        fecha_valor=contexto.fecha_valor,
        revision_prestamo=contexto.revision_prestamo,
        monto_recibido=contexto.monto_recibido,
        obligaciones=obligaciones,
    )


def simular_desde_cuotas_v3(
    *,
    prestamo_id: int,
    fecha_valor: date,
    revision_prestamo: int,
    monto_recibido: Decimal,
    cuotas: Iterable[CuotaMaterializada],
) -> PlanPago:
    """Ruta de conveniencia: cuotas existentes -> snapshot -> PlanPago."""
    contexto = ContextoSimulacionV3(
        prestamo_id=prestamo_id,
        fecha_valor=fecha_valor,
        revision_prestamo=revision_prestamo,
        monto_recibido=monto_recibido,
    )
    snapshots = mapear_cuotas_a_snapshot_v3(cuotas)
    return simular_plan_pago_v3(contexto=contexto, obligaciones=snapshots)
