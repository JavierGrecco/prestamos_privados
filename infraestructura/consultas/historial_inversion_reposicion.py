"""Adaptador de lectura para el historial declarado de inversión."""

from infraestructura.repositorios import PlanesReposicionRepo


class HistorialInversionReposicionSQLite:
    """Delegates historial y resumen al repositorio financiero existente."""

    def __init__(self, db) -> None:
        self._repo = PlanesReposicionRepo(db)

    def listar_flujos_inversion(self, plan_id: int, limite: int = 100):
        return self._repo.listar_flujos_inversion(plan_id, limite=limite)

    def listar_valuaciones_inversion(self, plan_id: int, limite: int = 100):
        return self._repo.listar_valuaciones_inversion(plan_id, limite=limite)

    def resumen_rendimiento_inversion(self, plan_id: int):
        return self._repo.resumen_rendimiento_inversion(plan_id)


__all__ = ["HistorialInversionReposicionSQLite"]
