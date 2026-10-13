"""Contrato de lectura mínima para validar la existencia de una persona."""

from __future__ import annotations

from typing import Protocol


class ConsultaExistenciaPersonaFinanciera(Protocol):
    """Permite validar que la persona consultada pertenece al sistema."""

    def existe(self, persona_id: int) -> bool: ...


__all__ = ["ConsultaExistenciaPersonaFinanciera"]
