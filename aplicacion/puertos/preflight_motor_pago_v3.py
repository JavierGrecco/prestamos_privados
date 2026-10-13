"""Puertos de lectura para evaluar si el Motor V3 está listo para activarse."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol


class InformeIntegridadV3Lectura(Protocol):
    """Resumen mínimo del resultado de la auditoría de integridad."""

    ok: bool
    cantidad_incidencias: int


class MetricasSombraV3Lectura(Protocol):
    """Métricas mínimas usadas como evidencia del preflight."""

    ejecuciones_sombra: int
    ejecuciones_con_divergencia: int
    ejecuciones_con_error: int
    tasa_coincidencia: Decimal | float | None


class ObtenerVersionSchema(Protocol):
    """Lee la versión de esquema vigente sin cambiar la base."""

    def __call__(self) -> int: ...


class AuditarIntegridadV3(Protocol):
    """Consulta la integridad financiera V3 sin repararla ni escribir."""

    def __call__(self) -> InformeIntegridadV3Lectura: ...


class ObtenerMetricasSombraV3(Protocol):
    """Lee métricas agregadas de SOMBRA sin efectos secundarios."""

    def __call__(self) -> MetricasSombraV3Lectura: ...


__all__ = [
    "InformeIntegridadV3Lectura",
    "MetricasSombraV3Lectura",
    "ObtenerVersionSchema",
    "AuditarIntegridadV3",
    "ObtenerMetricasSombraV3",
]
