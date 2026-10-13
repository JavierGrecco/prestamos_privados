"""Punto único de composición para consultas financieras de solo lectura.

La aplicación define contratos y coordina resultados. Este módulo conecta esos
contratos con las implementaciones SQLite usadas por la instalación local.
"""

from __future__ import annotations

from aplicacion.consultas.analisis_financiero import (
    AnalisisFinancieroQuery,
    ServicioAnalisisFinanciero,
)
from aplicacion.consultas.escenarios_persona import (
    EscenariosPersonaQuery,
    ServicioEscenariosPersona,
)
from aplicacion.consultas.rendimiento_financiero_persona import (
    RendimientoFinancieroPersonaQuery,
    ServicioRendimientoFinancieroPersona,
)
from aplicacion.consultas.planificacion_financiera_persona import (
    ServicioPlanificacionFinancieraPersona,
)
from infraestructura.consultas.analisis_financiero import AnalisisFinancieroSQLiteQuery
from infraestructura.consultas.persona_financiera import PersonaFinancieraSQLiteQuery


def crear_analisis_financiero_query(db) -> AnalisisFinancieroQuery:
    """Conecta el read model financiero con su lector SQLite."""
    return AnalisisFinancieroQuery(AnalisisFinancieroSQLiteQuery(db))


def crear_servicio_analisis_financiero(db) -> ServicioAnalisisFinanciero:
    """Devuelve el caso de uso de análisis con sus dependencias ya resueltas."""
    return ServicioAnalisisFinanciero(crear_analisis_financiero_query(db))


def crear_servicio_escenarios_persona(db) -> ServicioEscenariosPersona:
    """Conecta escenarios con un análisis financiero y un lector de personas."""
    consulta = EscenariosPersonaQuery(
        personas=PersonaFinancieraSQLiteQuery(db),
        analisis=crear_analisis_financiero_query(db),
    )
    return ServicioEscenariosPersona(consulta)


def crear_servicio_rendimiento_financiero_persona(
    db,
) -> ServicioRendimientoFinancieroPersona:
    """Conecta rendimiento explicado con el análisis financiero compartido."""
    consulta = RendimientoFinancieroPersonaQuery(
        personas=PersonaFinancieraSQLiteQuery(db),
        analisis=crear_analisis_financiero_query(db),
    )
    return ServicioRendimientoFinancieroPersona(consulta)


def crear_servicio_planificacion_financiera_persona(
    db,
) -> ServicioPlanificacionFinancieraPersona:
    """Conecta la planificación con el análisis financiero de solo lectura."""
    analisis = crear_analisis_financiero_query(db)
    return ServicioPlanificacionFinancieraPersona(db, analisis=analisis)


__all__ = [
    "crear_analisis_financiero_query",
    "crear_servicio_analisis_financiero",
    "crear_servicio_escenarios_persona",
    "crear_servicio_rendimiento_financiero_persona",
    "crear_servicio_planificacion_financiera_persona",
]
