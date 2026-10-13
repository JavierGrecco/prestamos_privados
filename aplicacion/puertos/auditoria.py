"""Contrato público de lectura de auditoría para casos de uso y UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class EntradaAuditoria:
    """Registro de auditoría presentado sin exponer el modelo SQLite."""

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
    """Lecturas de evidencia inmutable; este contrato no admite escrituras."""

    def listar(
        self,
        *,
        limite: int = 200,
        usuario: str | None = None,
        operacion: str | None = None,
        entidad: str | None = None,
    ) -> list[EntradaAuditoria]: ...

    def operaciones(self, *, limite: int = 100) -> list[str]: ...

    def entidades(self, *, limite: int = 100) -> list[str]: ...

    def por_correlacion(self, correlacion_id: str) -> list[EntradaAuditoria]: ...


__all__ = ["EntradaAuditoria", "ConsultaAuditoria"]
