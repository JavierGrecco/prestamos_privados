"""Composición local de la vista humana de Mi espacio."""

from __future__ import annotations

from aplicacion.consultas.vista_humana_persona import ServicioVistaHumanaPersona
from infraestructura.consultas.detalle_financiero_prestamo import (
    DetalleFinancieroPrestamoSQLiteQuery,
)


def crear_servicio_vista_humana_persona(db) -> ServicioVistaHumanaPersona:
    """Ensamble la vista humana con su lector de detalle SQLite."""
    return ServicioVistaHumanaPersona(
        db,
        detalle=DetalleFinancieroPrestamoSQLiteQuery(db),
    )


__all__ = ["crear_servicio_vista_humana_persona"]
