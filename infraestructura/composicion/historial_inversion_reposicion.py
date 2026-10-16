"""Punto de composición del historial de inversión declarada."""

from aplicacion.consultas.historial_inversion_reposicion import (
    ConsultaHistorialInversionReposicion,
)
from infraestructura.consultas.historial_inversion_reposicion import (
    HistorialInversionReposicionSQLite,
)


def crear_consulta_historial_inversion_reposicion(
    db,
) -> ConsultaHistorialInversionReposicion:
    """Conecta la consulta tipada con la lectura SQLite ya existente."""
    return ConsultaHistorialInversionReposicion(HistorialInversionReposicionSQLite(db))


__all__ = ["crear_consulta_historial_inversion_reposicion"]
