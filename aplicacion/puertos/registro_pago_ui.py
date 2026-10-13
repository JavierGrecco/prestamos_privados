"""Colaboradores públicos para el caso de uso de registro de pagos consumido por UI.

La interfaz coordina el flujo y las decisiones de modo; no debe construir
conexiones, repositorios ni fábricas concretas. La distribución local ensambla
estos colaboradores desde infraestructura/composicion.
"""

from __future__ import annotations

from typing import Any, Protocol


class ConfiguracionMotorPago(Protocol):
    """Lectura/cambio del modo efectivo del motor."""

    def obtener(self) -> Any: ...

    def cambiar(
        self,
        *,
        nuevo_modo: Any,
        usuario: str,
        motivo: str,
    ) -> Any: ...


class PreflightMotorPago(Protocol):
    """Evaluación previa requerida para habilitar V3."""

    def evaluar(self) -> Any: ...


class RegistrarPagoLegacy(Protocol):
    """Ejecuta el caso de uso histórico con los parámetros recibidos."""

    def __call__(self, **kwargs: Any) -> Any: ...


class CrearPuenteSombraPago(Protocol):
    """Construye el puente SOMBRA ligado a la misma unidad SQLite."""

    def __call__(self) -> Any: ...


class CrearRegistradorPagoV3(Protocol):
    """Construye el registrador V3 con la configuración contractual indicada."""

    def __call__(self, **kwargs: Any) -> Any: ...


__all__ = [
    "ConfiguracionMotorPago",
    "PreflightMotorPago",
    "RegistrarPagoLegacy",
    "CrearPuenteSombraPago",
    "CrearRegistradorPagoV3",
]
