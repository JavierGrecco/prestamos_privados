"""Composición local de la vista humana de Mi espacio."""

from __future__ import annotations

from aplicacion.consultas.vista_humana_persona import (
    ServicioVistaHumanaPersona,
    VistaHumanaPersonaQuery,
)
from infraestructura.composicion.analisis_financiero import (
    crear_analisis_financiero_query,
)
from infraestructura.consultas.detalle_financiero_prestamo import (
    DetalleFinancieroPrestamoSQLiteQuery,
)
from infraestructura.consultas.vista_humana_persona import VistaHumanaPersonaSQLiteQuery


def crear_servicio_vista_humana_persona(db) -> ServicioVistaHumanaPersona:
    """Ensamble la vista humana con su lector de detalle SQLite."""
    consulta = VistaHumanaPersonaQuery(
        datos=VistaHumanaPersonaSQLiteQuery(db),
        detalle=DetalleFinancieroPrestamoSQLiteQuery(db),
        analisis=crear_analisis_financiero_query(db),
    )
    return ServicioVistaHumanaPersona(consulta)


__all__ = ["crear_servicio_vista_humana_persona"]
