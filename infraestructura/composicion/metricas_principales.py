"""Fábrica pública del resumen financiero principal."""

from aplicacion.servicios.metricas_principales import ServicioMetricasPrincipales
from infraestructura.consultas.metricas_principales import LectorMetricasPrincipales


def crear_servicio_metricas_principales(db) -> ServicioMetricasPrincipales:
    """Ensambla el servicio con la lectura SQLite de esta instalación."""
    return ServicioMetricasPrincipales(LectorMetricasPrincipales(db))


__all__ = ["crear_servicio_metricas_principales"]
