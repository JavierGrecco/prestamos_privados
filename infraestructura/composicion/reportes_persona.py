"""Composición local de reportes financieros por persona."""

from __future__ import annotations

from aplicacion.servicios.reportes_persona import ServicioReportesPersona
from infraestructura.consultas.reportes_persona import ReportesPersonaSQLiteQuery
from infraestructura.composicion.posicion_financiera import (
    crear_servicio_posicion_financiera_persona,
)
from infraestructura.composicion.analisis_financiero import (
    crear_servicio_escenarios_persona,
    crear_servicio_rendimiento_financiero_persona,
    crear_servicio_planificacion_financiera_persona,
)


def crear_servicio_reportes_persona(db) -> ServicioReportesPersona:
    """Ensamble los reportes reutilizando la posición ya compuesta por contrato."""
    return ServicioReportesPersona(
        personas=ReportesPersonaSQLiteQuery(db),
        posicion=crear_servicio_posicion_financiera_persona(db),
        planificacion=crear_servicio_planificacion_financiera_persona(db),
        rendimiento=crear_servicio_rendimiento_financiero_persona(db),
        escenarios=crear_servicio_escenarios_persona(db),
    )


__all__ = ["crear_servicio_reportes_persona"]
