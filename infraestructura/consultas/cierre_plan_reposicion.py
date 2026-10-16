"""Adaptador SQLite para cerrar planes usando las reglas actuales."""

from infraestructura.repositorios import PlanesReposicionRepo


class CierrePlanReposicionSQLite:
    """Deriva el cierre al repositorio que conserva estado, auditoría y atomicidad."""

    def __init__(self, db) -> None:
        self._repo = PlanesReposicionRepo(db)

    def cerrar_plan(self, plan_id: int, *, cerrado_por: str) -> None:
        self._repo.cerrar_plan(plan_id, cerrado_por=cerrado_por)


__all__ = ["CierrePlanReposicionSQLite"]
