"""Drill reproducible de rollback operativo V3 -> Legacy.

El drill modela una transición entre operaciones. Nunca cambia de motor dentro
de una transacción que ya comenzó.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from aplicacion.servicios.feature_flag_motor_pago_v3 import (
    FeatureFlagMotorPagoV3,
)
from aplicacion.servicios.puente_motor_pago_v3 import ModoMotorPagoV3
from aplicacion.servicios.preflight_motor_pago_v3 import ResultadoPreflightV3
from dominio.excepciones import ErrorInvariante


ConstructorPuente = Callable[[ModoMotorPagoV3], Any]
ConstructorCommandLegacy = Callable[[], Any]


@dataclass(frozen=True)
class ResultadoDrillRollbackV3:
    decision_v3: Any
    resultado_v3: Any
    decision_legacy: Any
    resultado_legacy: Any


class DrillRollbackMotorPagoV3:
    """Ejecuta V3 y luego una operación posterior por Legacy."""

    def __init__(
        self,
        *,
        crear_puente: ConstructorPuente,
        selector: FeatureFlagMotorPagoV3 | None = None,
    ) -> None:
        self._crear_puente = crear_puente
        self._selector = selector or FeatureFlagMotorPagoV3()

    def ejecutar(
        self,
        *,
        command_v3: Any,
        construir_command_legacy: ConstructorCommandLegacy,
        preflight: ResultadoPreflightV3,
    ) -> ResultadoDrillRollbackV3:
        decision_v3 = self._selector.resolver(
            solicitado=ModoMotorPagoV3.V3,
            preflight=preflight,
        )
        if decision_v3.modo is not ModoMotorPagoV3.V3:
            raise ErrorInvariante("El drill no pudo habilitar V3")

        puente_v3 = self._crear_puente(ModoMotorPagoV3.V3)
        resultado_v3 = puente_v3.ejecutar(command_v3)

        # El comando Legacy debe construirse DESPUÉS de la operación V3,
        # porque el estado financiero ya cambió.
        command_legacy = construir_command_legacy()

        # El rollback es una decisión explícita para la siguiente operación.
        decision_legacy = self._selector.resolver(
            solicitado=ModoMotorPagoV3.LEGACY,
            preflight=preflight,
        )
        puente_legacy = self._crear_puente(ModoMotorPagoV3.LEGACY)
        resultado_legacy = puente_legacy.ejecutar(command_legacy)

        return ResultadoDrillRollbackV3(
            decision_v3=decision_v3,
            resultado_v3=resultado_v3,
            decision_legacy=decision_legacy,
            resultado_legacy=resultado_legacy,
        )
