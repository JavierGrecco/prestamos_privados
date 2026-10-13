"""Composición local del comparador de decisiones financieras."""

from __future__ import annotations

from aplicacion.consultas.comparador_decisiones_financieras import (
    ComparadorDecisionesFinancierasQuery,
    ServicioComparadorDecisionesFinancieras,
)
from infraestructura.composicion.analisis_financiero import (
    crear_analisis_financiero_query,
)


def crear_servicio_comparador_decisiones_financieras(
    db,
) -> ServicioComparadorDecisionesFinancieras:
    """Inyecta el análisis financiero compartido en el comparador M7."""
    consulta = ComparadorDecisionesFinancierasQuery(
        db,
        analisis=crear_analisis_financiero_query(db),
    )
    return ServicioComparadorDecisionesFinancieras(consulta)


__all__ = ["crear_servicio_comparador_decisiones_financieras"]
