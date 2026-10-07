"""Servicio de aplicación para consultar métricas de SOMBRA V3.

Es una fachada pequeña: la lógica de agregación permanece en la consulta de
infraestructura y este servicio no conoce Streamlit.
"""
from __future__ import annotations

from infraestructura.consultas.metricas_sombra_v3 import (
    MetricasSombraV3,
    MetricasSombraV3Query,
)


class ServicioMetricasSombraV3:
    """Expone métricas de adopción como caso de uso de solo lectura."""

    def __init__(self, db) -> None:
        self._consulta = MetricasSombraV3Query(db)

    def obtener(self, prestamo_id: int | None = None) -> MetricasSombraV3:
        return self._consulta.obtener(prestamo_id)


def obtener_metricas_sombra_v3(db, prestamo_id: int | None = None) -> MetricasSombraV3:
    return ServicioMetricasSombraV3(db).obtener(prestamo_id)
