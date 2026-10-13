"""Readiness operativa para el canary del Motor de Pagos V3."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from typing import TYPE_CHECKING

from aplicacion.puertos.registro_pago_ui import ConfiguracionMotorPago
from aplicacion.servicios.preflight_motor_pago_v3 import VERSION_MINIMA_SCHEMA_V3

if TYPE_CHECKING:
    from aplicacion.servicios.preflight_motor_pago_v3 import PreflightMotorPagoV3


@dataclass(frozen=True)
class ResultadoReadinessCanaryV3:
    listo: bool
    modo_actual: str
    revision_modo: int
    integridad_ok: bool
    preflight_apto: bool
    ejecuciones_sombra: int
    tasa_coincidencia: float | None
    divergencias: int
    errores: int
    motivos_rechazo: tuple[str, ...]


class ServicioReadinessCanaryV3:
    """Evalúa readiness sin modificar la configuración ni los hechos financieros."""

    def __init__(
        self,
        *,
        preflight: PreflightMotorPagoV3,
        configuracion: ConfiguracionMotorPago,
    ) -> None:
        """Recibe la misma evaluación de preflight usada para configurar el motor."""
        self._preflight = preflight
        self._configuracion = configuracion

    def evaluar(self) -> ResultadoReadinessCanaryV3:
        preflight = self._preflight.evaluar()
        estado = self._configuracion.obtener()

        if preflight.evidencia is None:
            raise RuntimeError("El preflight no devolvió evidencia de evaluación")
        evidencia = preflight.evidencia

        motivos = list(preflight.motivos_rechazo)
        if estado.modo.value not in {"LEGACY", "SOMBRA"}:
            motivos.append(
                f"El modo actual {estado.modo.value} no es un modo previo al canary"
            )
        listo = evidencia.integridad_ok and preflight.apto and estado.modo.value in {"LEGACY", "SOMBRA"}

        return ResultadoReadinessCanaryV3(
            listo=listo,
            modo_actual=estado.modo.value,
            revision_modo=estado.revision,
            integridad_ok=evidencia.integridad_ok,
            preflight_apto=preflight.apto,
            ejecuciones_sombra=evidencia.ejecuciones_sombra,
            tasa_coincidencia=evidencia.tasa_coincidencia,
            divergencias=evidencia.divergencias,
            errores=evidencia.errores,
            motivos_rechazo=tuple(motivos),
        )
