"""Composición SQLite del read model del detalle financiero de préstamos."""

from __future__ import annotations

from aplicacion.consultas.detalle_financiero_prestamo import (
    DetalleFinancieroPrestamoQuery,
    ServicioDetalleFinancieroPrestamo,
)
from infraestructura.consultas.detalle_financiero_prestamo import (
    DetalleFinancieroPrestamoSQLiteQuery,
)


def crear_consulta_detalle_financiero_prestamo(db) -> DetalleFinancieroPrestamoQuery:
    """Construye la consulta de aplicación con su adaptador SQLite."""
    return DetalleFinancieroPrestamoQuery(
        DetalleFinancieroPrestamoSQLiteQuery(db)
    )


def crear_servicio_detalle_financiero_prestamo(
    db,
) -> ServicioDetalleFinancieroPrestamo:
    """Construye el caso de uso de lectura para UI/exportaciones locales."""
    return ServicioDetalleFinancieroPrestamo(
        DetalleFinancieroPrestamoSQLiteQuery(db)
    )


__all__ = [
    "crear_consulta_detalle_financiero_prestamo",
    "crear_servicio_detalle_financiero_prestamo",
]
