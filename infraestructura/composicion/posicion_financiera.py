"""Composición SQLite de la posición financiera consolidada de una persona."""

from __future__ import annotations

from aplicacion.consultas.analisis_financiero import AnalisisFinancieroQuery
from aplicacion.consultas.posicion_financiera_persona import (
    PosicionFinancieraPersonaQuery,
    ServicioPosicionFinancieraPersona,
)
from infraestructura.consultas.persona_financiera import PersonaFinancieraSQLiteQuery


def crear_servicio_posicion_financiera_persona(
    db,
) -> ServicioPosicionFinancieraPersona:
    """Ensambla la posición con el lector de persona y el análisis existente."""
    consulta = PosicionFinancieraPersonaQuery(
        personas=PersonaFinancieraSQLiteQuery(db),
        analisis=AnalisisFinancieroQuery(db),
    )
    return ServicioPosicionFinancieraPersona(consulta=consulta)


__all__ = ["crear_servicio_posicion_financiera_persona"]
