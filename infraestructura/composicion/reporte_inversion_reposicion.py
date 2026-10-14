"""Composición local del reporte interno de reposición e inversión."""

from __future__ import annotations

from aplicacion.servicios.reporte_inversion_reposicion import (
    ServicioReporteInversionReposicion,
)
from infraestructura.consultas.reporte_inversion_reposicion import (
    ReporteInversionReposicionSQLiteQuery,
)


def crear_servicio_reporte_inversion_reposicion(
    db,
) -> ServicioReporteInversionReposicion:
    """Conecta el reporte a las lecturas verificadas del repositorio SQLite."""
    return ServicioReporteInversionReposicion(
        ReporteInversionReposicionSQLiteQuery(db)
    )


__all__ = ["crear_servicio_reporte_inversion_reposicion"]
