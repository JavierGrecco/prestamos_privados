"""Composición del caso de uso para cerrar un plan de reposición."""

from aplicacion.servicios.cerrar_plan_reposicion import ServicioCerrarPlanReposicion
from infraestructura.consultas.cierre_plan_reposicion import CierrePlanReposicionSQLite


def crear_servicio_cerrar_plan_reposicion(db) -> ServicioCerrarPlanReposicion:
    """Conecta la operación de aplicación con la persistencia SQLite."""
    return ServicioCerrarPlanReposicion(CierrePlanReposicionSQLite(db))


__all__ = ["crear_servicio_cerrar_plan_reposicion"]
