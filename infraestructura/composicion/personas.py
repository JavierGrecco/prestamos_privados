"""Composición SQLite del servicio de personas."""

from __future__ import annotations

from aplicacion.servicios.personas import ServicioPersonas
from infraestructura.repositorios import (
    GarantiaPrestamoRepo,
    ParticipacionRepo,
    PersonaRepo,
    PrestamoRepo,
)


def crear_servicio_personas(db) -> ServicioPersonas:
    """Ensamble el caso de uso con los repositorios SQLite concretos."""
    return ServicioPersonas(
        personas=PersonaRepo(db),
        prestamos=PrestamoRepo(db),
        participaciones=ParticipacionRepo(db),
        garantias=GarantiaPrestamoRepo(db),
    )


__all__ = ["crear_servicio_personas"]
