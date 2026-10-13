"""Composición local de reportes financieros por persona."""

from __future__ import annotations

from aplicacion.servicios.reportes_persona import ServicioReportesPersona
from infraestructura.composicion.posicion_financiera import (
    crear_servicio_posicion_financiera_persona,
)


def crear_servicio_reportes_persona(db) -> ServicioReportesPersona:
    """Ensamble los reportes reutilizando la posición ya compuesta por contrato."""
    return ServicioReportesPersona(
        db,
        posicion=crear_servicio_posicion_financiera_persona(db),
    )


__all__ = ["crear_servicio_reportes_persona"]
