"""Gate de preflight para una futura activación controlada de V3.

Este servicio es de solo lectura: no ejecuta pagos ni cambia el modo del
puente. Convierte señales técnicas y de observabilidad en criterios explícitos.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from aplicacion.puertos.preflight_motor_pago_v3 import (
    VERSION_MINIMA_SCHEMA_V3,
    AuditarIntegridadV3,
    ObtenerMetricasSombraV3,
    ObtenerVersionSchema,
)


@dataclass(frozen=True)
class CriterioPreflightV3:
    nombre: str
    cumplido: bool
    detalle: str


@dataclass(frozen=True)
class EvidenciaPreflightV3:
    """Observaciones capturadas en una única evaluación de preflight."""

    schema_actual: int
    integridad_ok: bool
    ejecuciones_sombra: int
    tasa_coincidencia: Decimal | None
    divergencias: int
    errores: int


@dataclass(frozen=True)
class ResultadoPreflightV3:
    apto: bool
    criterios: tuple[CriterioPreflightV3, ...]
    evidencia: EvidenciaPreflightV3 | None = None

    @property
    def motivos_rechazo(self) -> tuple[str, ...]:
        return tuple(c.detalle for c in self.criterios if not c.cumplido)


class PreflightMotorPagoV3:
    """Evalúa si el sistema cumple los criterios configurados para cut-over."""

    def __init__(
        self,
        *,
        obtener_version_schema: ObtenerVersionSchema,
        auditar_integridad: AuditarIntegridadV3,
        obtener_metricas_sombra: ObtenerMetricasSombraV3,
        version_minima: int = VERSION_MINIMA_SCHEMA_V3,
        ejecuciones_minimas: int = 100,
        tasa_coincidencia_minima: Decimal = Decimal("1"),
        divergencias_maximas: int = 0,
        errores_maximos: int = 0,
    ) -> None:
        if version_minima <= 0:
            raise ValueError("version_minima debe ser positiva")
        if ejecuciones_minimas < 0:
            raise ValueError("ejecuciones_minimas no puede ser negativa")
        if not 0 <= tasa_coincidencia_minima <= 1:
            raise ValueError("tasa_coincidencia_minima debe estar entre 0 y 1")
        if divergencias_maximas < 0 or errores_maximos < 0:
            raise ValueError("los máximos permitidos no pueden ser negativos")

        self._obtener_version_schema = obtener_version_schema
        self._auditar_integridad = auditar_integridad
        self._obtener_metricas_sombra = obtener_metricas_sombra
        self._version_minima = version_minima
        self._ejecuciones_minimas = ejecuciones_minimas
        self._tasa_coincidencia_minima = tasa_coincidencia_minima
        self._divergencias_maximas = divergencias_maximas
        self._errores_maximos = errores_maximos

    def evaluar(self) -> ResultadoPreflightV3:
        criterios = []

        version = self._obtener_version_schema()
        criterios.append(
            CriterioPreflightV3(
                "schema",
                version >= self._version_minima,
                f"Schema v{version:03d}; mínimo requerido v{self._version_minima:03d}",
            )
        )

        integridad = self._auditar_integridad()
        criterios.append(
            CriterioPreflightV3(
                "integridad_v3",
                integridad.ok,
                (
                    "Integridad V3 sin incidencias"
                    if integridad.ok
                    else f"Integridad V3 con {integridad.cantidad_incidencias} incidencia(s)"
                ),
            )
        )

        metricas = self._obtener_metricas_sombra()
        criterios.append(
            CriterioPreflightV3(
                "ejecuciones_minimas",
                metricas.ejecuciones_sombra >= self._ejecuciones_minimas,
                f"Ejecuciones SOMBRA: {metricas.ejecuciones_sombra}; mínimo: {self._ejecuciones_minimas}",
            )
        )

        criterios.append(
            CriterioPreflightV3(
                "divergencias_maximas",
                metricas.ejecuciones_con_divergencia <= self._divergencias_maximas,
                f"Divergencias: {metricas.ejecuciones_con_divergencia}; máximo: {self._divergencias_maximas}",
            )
        )

        criterios.append(
            CriterioPreflightV3(
                "errores_maximos",
                metricas.ejecuciones_con_error <= self._errores_maximos,
                f"Errores SOMBRA: {metricas.ejecuciones_con_error}; máximo: {self._errores_maximos}",
            )
        )

        tasa = metricas.tasa_coincidencia
        tasa_ok = (
            tasa is not None
            and Decimal(str(tasa)) >= self._tasa_coincidencia_minima
        )
        criterios.append(
            CriterioPreflightV3(
                "tasa_coincidencia",
                tasa_ok,
                (
                    f"Tasa de coincidencia: {tasa!r}; "
                    f"mínimo: {self._tasa_coincidencia_minima}"
                ),
            )
        )

        return ResultadoPreflightV3(
            apto=all(c.cumplido for c in criterios),
            criterios=tuple(criterios),
            evidencia=EvidenciaPreflightV3(
                schema_actual=version,
                integridad_ok=integridad.ok,
                ejecuciones_sombra=metricas.ejecuciones_sombra,
                tasa_coincidencia=metricas.tasa_coincidencia,
                divergencias=metricas.ejecuciones_con_divergencia,
                errores=metricas.ejecuciones_con_error,
            ),
        )
