"""Contratos de resultados del modo SOMBRA del motor de pagos V3.

El servicio genera estas observaciones y la infraestructura las registra. Los
tipos compartidos viven aquí para que la persistencia no dependa de la clase
concreta que ejecuta el puente Legacy/V3.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from aplicacion.puertos.registro_pago_v3 import EstadoRegistroPagoV3

from dominio.excepciones import ErrorInvariante


class ResultadoEjecucionSombraV3(str, Enum):
    SIN_DIVERGENCIA = "SIN_DIVERGENCIA"
    DIVERGENCIA = "DIVERGENCIA"
    ERROR_SOMBRA = "ERROR_SOMBRA"


@dataclass(frozen=True)
class DivergenciaMotorPagoV3:
    fingerprint: str
    resumen: str
    tipo: str = "DIVERGENCIA"
    prestamo_id: int | None = None
    pago_legacy_id: int | None = None

    def __post_init__(self) -> None:
        if not self.fingerprint.strip():
            raise ErrorInvariante("La divergencia debe estar asociada a una huella")
        if not self.resumen.strip():
            raise ErrorInvariante("La divergencia debe tener un resumen")
        if self.tipo not in {"DIVERGENCIA", "ERROR_SOMBRA"}:
            raise ErrorInvariante("Tipo de observación SOMBRA inválido")
        if self.prestamo_id is not None and self.prestamo_id <= 0:
            raise ErrorInvariante("El préstamo de la observación debe ser positivo")
        if self.pago_legacy_id is not None and self.pago_legacy_id <= 0:
            raise ErrorInvariante("El pago Legacy de la observación debe ser positivo")


@dataclass(frozen=True)
class EjecucionSombraMotorPagoV3:
    fingerprint: str
    prestamo_id: int
    pago_legacy_id: int | None
    resultado: ResultadoEjecucionSombraV3
    revision_snapshot: int | None
    resumen: str | None

class ConsultaEstadoPagoSombraV3(Protocol):
    """Consulta de solo lectura usada para capturar el estado previo a Legacy."""

    def obtener_estado_pago(self, prestamo_id: int) -> EstadoRegistroPagoV3: ...

