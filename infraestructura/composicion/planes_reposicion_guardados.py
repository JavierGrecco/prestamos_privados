"""Punto de composición de la consulta de planes guardados."""

from aplicacion.consultas.planes_reposicion_guardados import (
    ConsultaPlanesReposicionGuardados,
)
from infraestructura.consultas.planes_reposicion_guardados import (
    PlanesReposicionGuardadosSQLite,
)


def crear_consulta_planes_reposicion_guardados(
    db,
) -> ConsultaPlanesReposicionGuardados:
    """Conecta la consulta de aplicación con la lectura local de SQLite."""
    return ConsultaPlanesReposicionGuardados(PlanesReposicionGuardadosSQLite(db))


__all__ = ["crear_consulta_planes_reposicion_guardados"]
