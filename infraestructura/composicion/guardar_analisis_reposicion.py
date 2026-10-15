"""Composición del caso de uso para guardar análisis de reposición."""

from aplicacion.servicios.guardar_analisis_reposicion import (
    ServicioGuardarAnalisisReposicion,
)
from infraestructura.consultas.guardado_analisis_reposicion import (
    GuardadoAnalisisReposicionSQLite,
)


def crear_servicio_guardado_analisis_reposicion(
    db,
) -> ServicioGuardarAnalisisReposicion:
    """Conecta el caso de uso con la persistencia SQLite existente."""
    return ServicioGuardarAnalisisReposicion(GuardadoAnalisisReposicionSQLite(db))


__all__ = ["crear_servicio_guardado_analisis_reposicion"]
