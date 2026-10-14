"""Composición SQLite del servicio de préstamos."""

from __future__ import annotations

from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura.adaptadores.unidad_trabajo_prestamos import (
    UnidadTrabajoPrestamosSQLite,
)
from infraestructura.repositorios import (
    AuditoriaRepo,
    LedgerRepo,
    ParticipacionRepo,
    PersonaRepo,
    PrestamoRepo,
)


def crear_servicio_prestamos(db) -> ServicioPrestamos:
    """Ensamble repositorios y unidad de trabajo en la frontera de infraestructura."""
    return ServicioPrestamos(
        personas=PersonaRepo(db),
        prestamos=PrestamoRepo(db),
        participaciones=ParticipacionRepo(db),
        ledger=LedgerRepo(db),
        auditoria=AuditoriaRepo(db),
        unidad_trabajo=UnidadTrabajoPrestamosSQLite(db),
    )


__all__ = ["crear_servicio_prestamos"]
