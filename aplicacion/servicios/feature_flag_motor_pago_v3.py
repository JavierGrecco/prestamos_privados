"""Selector de modo para una activación controlada de V3.

No ejecuta pagos. Su única responsabilidad es convertir una configuración
solicitada y un resultado de preflight en un modo permitido.
"""
from __future__ import annotations

from dataclasses import dataclass

from aplicacion.servicios.puente_motor_pago_v3 import ModoMotorPagoV3
from aplicacion.servicios.preflight_motor_pago_v3 import ResultadoPreflightV3
from dominio.excepciones import ErrorValidacion


@dataclass(frozen=True)
class DecisionModoMotorPagoV3:
    modo: ModoMotorPagoV3
    solicitado: ModoMotorPagoV3
    preflight_apto: bool
    motivo: str


class FeatureFlagMotorPagoV3:
    """Resuelve el modo efectivo con una política fail-safe."""

    def resolver(
        self,
        *,
        solicitado: ModoMotorPagoV3 | str | None,
        preflight: ResultadoPreflightV3 | None = None,
    ) -> DecisionModoMotorPagoV3:
        if solicitado is None:
            return DecisionModoMotorPagoV3(
                modo=ModoMotorPagoV3.LEGACY,
                solicitado=ModoMotorPagoV3.LEGACY,
                preflight_apto=False if preflight is None else preflight.apto,
                motivo="No se solicitó un modo explícito; se mantiene LEGACY",
            )

        try:
            modo = ModoMotorPagoV3(solicitado)
        except ValueError as exc:
            raise ErrorValidacion(
                f"Modo de Motor de Pagos V3 inválido: {solicitado!r}"
            ) from exc

        if modo is not ModoMotorPagoV3.V3:
            return DecisionModoMotorPagoV3(
                modo=modo,
                solicitado=modo,
                preflight_apto=False if preflight is None else preflight.apto,
                motivo=f"Modo explícito permitido: {modo.value}",
            )

        if preflight is None:
            raise ErrorValidacion(
                "No se puede activar V3 sin resultado de preflight"
            )

        if not preflight.apto:
            raise ErrorValidacion(
                "No se puede activar V3: el preflight no está aprobado"
            )

        return DecisionModoMotorPagoV3(
            modo=ModoMotorPagoV3.V3,
            solicitado=modo,
            preflight_apto=True,
            motivo="V3 habilitado por preflight aprobado",
        )


def resolver_modo_motor_pago_v3(
    solicitado: ModoMotorPagoV3 | str | None,
    preflight: ResultadoPreflightV3 | None = None,
) -> DecisionModoMotorPagoV3:
    return FeatureFlagMotorPagoV3().resolver(
        solicitado=solicitado,
        preflight=preflight,
    )
