"""Adaptador para guardar un análisis mediante el repositorio local existente.

El adaptador no replica reglas: deriva creación, versiones inmutables,
validaciones y transacciones al repositorio que ya las implementa.
"""
from __future__ import annotations

from infraestructura.repositorios import PlanesReposicionRepo


class GuardadoAnalisisReposicionSQLite:
    """Implementación SQLite del puerto de guardado de análisis."""

    def __init__(self, db) -> None:
        self._repo = PlanesReposicionRepo(db)

    def crear_plan_con_snapshot(self, **kwargs):
        return self._repo.crear_plan_con_snapshot(**kwargs)

    def guardar_nueva_version(self, plan_id: int, **kwargs) -> int:
        return self._repo.guardar_nueva_version(plan_id, **kwargs)


__all__ = ["GuardadoAnalisisReposicionSQLite"]
