"""Punto de composición del historial de aportes de reposición."""

from aplicacion.consultas.historial_aportes_reposicion import (
    ConsultaHistorialAportesReposicion,
)
from infraestructura.consultas.historial_aportes_reposicion import (
    HistorialAportesReposicionSQLite,
)


def crear_consulta_historial_aportes_reposicion(
    db,
) -> ConsultaHistorialAportesReposicion:
    """Conecta la consulta tipada con la persistencia local."""
    return ConsultaHistorialAportesReposicion(HistorialAportesReposicionSQLite(db))


__all__ = ["crear_consulta_historial_aportes_reposicion"]
