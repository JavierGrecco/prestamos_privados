"""Contratos públicos para la lectura de métricas y observaciones SOMBRA V3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ConteoSombraV3:
    etiqueta: str
    cantidad: int


@dataclass(frozen=True)
class MetricasSombraV3:
    total_observaciones: int
    divergencias: int
    errores_sombra: int
    ejecuciones_sombra: int
    ejecuciones_sin_divergencia: int
    ejecuciones_con_divergencia: int
    ejecuciones_con_error: int
    prestamos_con_observaciones: int
    fingerprints_distintos: int
    primera_observacion: str | None
    ultima_observacion: str | None
    por_tipo: tuple[ConteoSombraV3, ...]
    por_prestamo: tuple[ConteoSombraV3, ...]
    por_fingerprint: tuple[ConteoSombraV3, ...]

    @property
    def observaciones_con_error(self) -> int:
        return self.errores_sombra

    @property
    def tasa_coincidencia(self) -> float | None:
        if self.ejecuciones_sombra == 0:
            return None
        return self.ejecuciones_sin_divergencia / self.ejecuciones_sombra

    @property
    def tasa_divergencia(self) -> float | None:
        if self.ejecuciones_sombra == 0:
            return None
        return self.ejecuciones_con_divergencia / self.ejecuciones_sombra

    @property
    def tasa_error(self) -> float | None:
        if self.ejecuciones_sombra == 0:
            return None
        return self.ejecuciones_con_error / self.ejecuciones_sombra

    @property
    def hay_observaciones(self) -> bool:
        return self.total_observaciones > 0


class ConsultaMetricasSombraV3(Protocol):
    """Lecturas agregadas y de observabilidad; nunca mutan hechos financieros."""

    def obtener(self, prestamo_id: int | None = None) -> MetricasSombraV3: ...

    def observaciones(
        self,
        *,
        prestamo_id: int | None = None,
        tipo: str | None = None,
        limite: int = 100,
    ) -> tuple[dict, ...]: ...


__all__ = [
    "ConteoSombraV3",
    "MetricasSombraV3",
    "ConsultaMetricasSombraV3",
]
