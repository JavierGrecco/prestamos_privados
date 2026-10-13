"""Contrato público de lectura para la evidencia de auditoría."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EventoAuditoria:
    """Modelo de lectura estable; no expone modelos ni filas de persistencia."""

    id: int | None = None
    fecha: str = ""
    usuario: str = ""
    operacion: str = ""
    entidad: str = ""
    entidad_id: int | None = None
    datos_anteriores: str | None = None
    datos_nuevos: str | None = None
    motivo: str | None = None
    correlacion_id: str = ""


class ConsultaAuditoria(Protocol):
    """Lecturas de auditoría disponibles para los casos de uso."""

    def listar(
        self,
        *,
        limite: int = 200,
        usuario: str | None = None,
        operacion: str | None = None,
        entidad: str | None = None,
    ) -> list[EventoAuditoria]: ...

    def operaciones(self, *, limite: int = 100) -> list[str]: ...

    def entidades(self, *, limite: int = 100) -> list[str]: ...

    def por_correlacion(self, correlacion_id: str) -> list[EventoAuditoria]: ...


__all__ = ["EventoAuditoria", "ConsultaAuditoria"]
