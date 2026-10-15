"""Adaptador de consulta de planes guardados sobre el repositorio local.

Este adaptador solo traduce la API existente al puerto de lectura; no escribe
datos ni recalcula resultados financieros.
"""
from __future__ import annotations

from infraestructura.repositorios import PlanesReposicionRepo


class PlanesReposicionGuardadosSQLite:
    """Implementa el puerto de lectura reutilizando la persistencia existente."""

    def __init__(self, db) -> None:
        self._repo = PlanesReposicionRepo(db)

    def listar_planes(self, limite: int = 30, *, solo_activos: bool = False):
        return self._repo.listar_planes(limite=limite, solo_activos=solo_activos)

    def obtener_plan(self, plan_id: int):
        return self._repo.obtener_plan(plan_id)

    def listar_versiones(self, plan_id: int):
        return self._repo.listar_versiones(plan_id)

    def obtener_version(self, plan_id: int, numero_version: int):
        return self._repo.obtener_version(plan_id, numero_version)

    def verificar_version(self, version) -> bool:
        return self._repo.verificar_version(version)


__all__ = ["PlanesReposicionGuardadosSQLite"]
