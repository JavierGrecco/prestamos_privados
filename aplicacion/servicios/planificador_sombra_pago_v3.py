"""Planificación de pagos V3 en modo SOMBRA sobre un snapshot previo a Legacy.

El planificador coordina una lectura inmutable y el cálculo puro del dominio.
No conoce SQLite ni persiste efectos secundarios.
"""

from __future__ import annotations

from typing import Any, Callable

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.puertos.registro_pago_v3 import EstadoRegistroPagoV3
from aplicacion.puertos.sombra_pago_v3 import ConsultaEstadoPagoSombraV3
from dominio.motor_pagos_v3 import calcular_plan_pago


CalculadorPlanSombraV3 = Callable[..., Any]


class PlanificadorSombraPagoV3:
    """Captura el snapshot una vez y planifica V3 sin volver a leer el estado."""

    def __init__(
        self,
        consulta: ConsultaEstadoPagoSombraV3,
        calculador_plan: CalculadorPlanSombraV3 = calcular_plan_pago,
    ) -> None:
        self._consulta = consulta
        self._calculador = calculador_plan

    def capturar_snapshot(
        self,
        command: RegistrarPagoCommand,
    ) -> EstadoRegistroPagoV3:
        """Obtiene el estado económico que debe existir antes de ejecutar Legacy."""
        return self._consulta.obtener_estado_pago(command.prestamo_id)

    def planificar(
        self,
        command: RegistrarPagoCommand,
        snapshot: EstadoRegistroPagoV3,
    ) -> Any:
        """Calcula usando exclusivamente el snapshot; no relee ni persiste."""
        if snapshot.prestamo_id != command.prestamo_id:
            raise ValueError(
                "El snapshot no corresponde al préstamo del comando"
            )

        return self._calculador(
            prestamo_id=snapshot.prestamo_id,
            fecha_valor=command.fecha_valor,
            revision_prestamo=snapshot.revision_prestamo,
            monto_recibido=command.monto,
            obligaciones=tuple(snapshot.obligaciones),
        )


__all__ = ["CalculadorPlanSombraV3", "PlanificadorSombraPagoV3"]
