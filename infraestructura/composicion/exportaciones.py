"""Composición SQLite de los read models para exportaciones."""

from __future__ import annotations

from aplicacion.servicios.exportaciones import ServicioExportaciones
from infraestructura.composicion.auditoria import crear_servicio_auditoria


def crear_servicio_exportaciones(db) -> ServicioExportaciones:
    """Ensambla exportaciones con el caso de uso público de consulta de auditoría."""
    return ServicioExportaciones(
        db,
        auditoria=crear_servicio_auditoria(db),
    )


__all__ = ["crear_servicio_exportaciones"]
