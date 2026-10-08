"""Readiness operativa para el canary del Motor de Pagos V3."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from aplicacion.servicios.configuracion_motor_pago import ServicioConfiguracionMotorPago
from aplicacion.servicios.preflight_motor_pago_v3 import (
    VERSION_MINIMA_SCHEMA_V3,
    PreflightMotorPagoV3,
)


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
        db,
        *,
        ejecuciones_minimas: int = 100,
        tasa_coincidencia_minima: Decimal = Decimal("1"),
        divergencias_maximas: int = 0,
        errores_maximos: int = 0,
    ) -> None:
        self._db = db
        self._ejecuciones_minimas = ejecuciones_minimas
        self._tasa_coincidencia_minima = tasa_coincidencia_minima
        self._divergencias_maximas = divergencias_maximas
        self._errores_maximos = errores_maximos

    def evaluar(self) -> ResultadoReadinessCanaryV3:
        preflight = PreflightMotorPagoV3(
            self._db,
            version_minima=VERSION_MINIMA_SCHEMA_V3,
            ejecuciones_minimas=self._ejecuciones_minimas,
            tasa_coincidencia_minima=self._tasa_coincidencia_minima,
            divergencias_maximas=self._divergencias_maximas,
            errores_maximos=self._errores_maximos,
        ).evaluar()
        estado = ServicioConfiguracionMotorPago(self._db).obtener()

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
