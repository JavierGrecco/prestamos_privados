"""Adaptador SQLite para leer el historial de aportes de reposición."""

from infraestructura.repositorios import PlanesReposicionRepo


class HistorialAportesReposicionSQLite:
    """Reutiliza el repositorio que define orden y límite del historial."""

    def __init__(self, db) -> None:
        self._repo = PlanesReposicionRepo(db)

    def listar_aportes(self, plan_id: int, limite: int = 200):
        return self._repo.listar_aportes(plan_id, limite=limite)


__all__ = ["HistorialAportesReposicionSQLite"]
