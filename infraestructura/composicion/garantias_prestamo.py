"""Composición SQLite para el servicio de garantías personales."""

from __future__ import annotations

from aplicacion.servicios.garantias_prestamo import ServicioGarantiasPrestamo
from infraestructura.adaptadores.unidad_trabajo_garantias import (
    UnidadTrabajoGarantiasSQLite,
)
from infraestructura.repositorios import (
    AuditoriaRepo,
    GarantiaPrestamoRepo,
    PersonaRepo,
    PrestamoRepo,
)


def crear_servicio_garantias_prestamo(db) -> ServicioGarantiasPrestamo:
    """Ensamble el servicio con repositorios y unidad de trabajo SQLite."""
    return ServicioGarantiasPrestamo(
        garantias=GarantiaPrestamoRepo(db),
        personas=PersonaRepo(db),
        prestamos=PrestamoRepo(db),
        auditoria=AuditoriaRepo(db),
        unidad_trabajo=UnidadTrabajoGarantiasSQLite(db),
    )


__all__ = ["crear_servicio_garantias_prestamo"]
