"""Servicio de aplicación para consultar métricas de SOMBRA V3.

Es una fachada pequeña: la lógica de agregación permanece en la consulta de
infraestructura y este servicio no conoce Streamlit.
"""
from __future__ import annotations

from aplicacion.puertos.metricas_sombra_v3 import (
    ConsultaMetricasSombraV3,
    ConteoSombraV3,
    MetricasSombraV3,
)


class ServicioMetricasSombraV3:
    """Expone métricas de adopción como caso de uso de solo lectura."""

    def __init__(self, consulta: ConsultaMetricasSombraV3) -> None:
        """Recibe una consulta de lectura sin conocer su implementación de persistencia."""
        self._consulta = consulta

    def obtener(self, prestamo_id: int | None = None) -> MetricasSombraV3:
        return self._consulta.obtener(prestamo_id)

    def observaciones(
        self,
        *,
        prestamo_id: int | None = None,
        tipo: str | None = None,
        limite: int = 100,
    ) -> tuple[dict, ...]:
        """Devuelve incidencias SOMBRA para revisión operativa, en modo solo lectura."""
        if tipo is not None and tipo not in {"DIVERGENCIA", "ERROR_SOMBRA"}:
            raise ValueError("tipo de observación inválido")
        return self._consulta.observaciones(
            prestamo_id=prestamo_id,
            tipo=tipo,
            limite=limite,
        )


def obtener_metricas_sombra_v3(
    consulta: ConsultaMetricasSombraV3,
    prestamo_id: int | None = None,
) -> MetricasSombraV3:
    """Función de aplicación equivalente a la lectura por servicio."""
    return ServicioMetricasSombraV3(consulta).obtener(prestamo_id)
