"""Adaptador de lectura SQLite para validar personas en consultas financieras."""

from __future__ import annotations

from infraestructura.repositorios import PersonaRepo


class PersonaFinancieraSQLiteQuery:
    """Adapta la consulta de existencia al repositorio SQLite existente."""

    def __init__(self, db) -> None:
        self._personas = PersonaRepo(db)

    def existe(self, persona_id: int) -> bool:
        return self._personas.obtener(persona_id) is not None


__all__ = ["PersonaFinancieraSQLiteQuery"]
