"""Contratos públicos para la configuración persistente del Motor de Pagos."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class ModoMotorPagoV3(str, Enum):
    LEGACY = "LEGACY"
    SOMBRA = "SOMBRA"
    V3 = "V3"


@dataclass(frozen=True, slots=True)
class EstadoConfiguracionMotorPago:
    """Estado de configuración que puede consumir aplicación e interfaz."""

    modo: ModoMotorPagoV3
    revision: int
    actualizado_en: str
    actualizado_por: str


class PersistenciaConfiguracionMotorPago(Protocol):
    """Lectura y cambio auditado de modo con concurrencia optimista."""

    def obtener(self) -> EstadoConfiguracionMotorPago: ...

    def cambiar_y_auditar(
        self,
        *,
        nuevo_modo: ModoMotorPagoV3,
        usuario: str,
        motivo: str,
        revision_esperada: int,
        correlacion_id: str,
    ) -> None:
        """Actualiza el modo y su auditoría en una misma transacción."""
        ...


__all__ = [
    "EstadoConfiguracionMotorPago",
    "PersistenciaConfiguracionMotorPago",
]
