"""Servicio de consulta para el resumen financiero principal.

El servicio une una fuente de datos con el cálculo de aplicación. No abre
conexiones ni construye repositorios: la implementación concreta se arma en
infraestructura/composicion.
"""
from __future__ import annotations

from typing import Protocol

from aplicacion.consultas.metricas_principales import (
    DatosMetricasPrincipales,
    INFLACION_MENSUAL_DEFAULT,
    MetricasPrincipales,
    calcular_metricas_principales,
)


class FuenteMetricasPrincipales(Protocol):
    """Contrato de lectura con los datos mínimos para el resumen."""

    def obtener(self, persona_id: int) -> DatosMetricasPrincipales:
        """Devuelve los datos financieros necesarios para una persona."""


class ServicioMetricasPrincipales:
    """Entrega métricas calculadas sin depender del detalle de persistencia."""

    def __init__(self, fuente: FuenteMetricasPrincipales) -> None:
        self._fuente = fuente

    def obtener(
        self,
        persona_id: int,
        inflacion_mensual=INFLACION_MENSUAL_DEFAULT,
    ) -> MetricasPrincipales:
        """Lee los datos de la persona y devuelve el resumen calculado."""
        datos = self._fuente.obtener(persona_id)
        return calcular_metricas_principales(datos, inflacion_mensual)


__all__ = [
    "FuenteMetricasPrincipales",
    "ServicioMetricasPrincipales",
]
