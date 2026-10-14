"""Consultas SQLite mínimas para el vínculo opcional cuenta-persona."""

from __future__ import annotations

from collections.abc import Sequence

from aplicacion.puertos.usuarios_locales import (
    ConsultaPersonasUsuariosLocales,
    PersonaVinculable,
)
from infraestructura.repositorios import PersonaRepo


class ConsultaPersonasUsuariosLocalesSQLite:
    """Oculta el repositorio concreto detrás del contrato que usa la aplicación/UI."""

    def __init__(self, db) -> None:
        self._personas = PersonaRepo(db)

    def obtener(self, persona_id: int) -> PersonaVinculable | None:
        return self._personas.obtener(persona_id)

    def listar(
        self, estado: str | None = None
    ) -> Sequence[PersonaVinculable]:
        return tuple(self._personas.listar(estado=estado))


__all__ = ["ConsultaPersonasUsuariosLocalesSQLite"]
