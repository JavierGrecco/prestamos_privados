"""Servicio de aplicación para consultar métricas de SOMBRA V3.

Es una fachada pequeña: la lógica de agregación permanece en la consulta de
infraestructura y este servicio no conoce Streamlit.
"""
from __future__ import annotations

from infraestructura.consultas.metricas_sombra_v3 import (
    MetricasSombraV3,
    MetricasSombraV3Query,
)
from infraestructura.repositorios.observaciones_sombra_v3 import ObservacionesSombraV3Repo


class ServicioMetricasSombraV3:
    """Expone métricas de adopción como caso de uso de solo lectura."""

    def __init__(self, db) -> None:
        self._consulta = MetricasSombraV3Query(db)

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
        if limite <= 0:
            raise ValueError("limite debe ser positivo")
        if tipo is not None and tipo not in {"DIVERGENCIA", "ERROR_SOMBRA"}:
            raise ValueError("tipo de observación inválido")
        if prestamo_id is not None and prestamo_id <= 0:
            raise ValueError("prestamo_id debe ser positivo")

        if prestamo_id is not None:
            filas = ObservacionesSombraV3Repo(self._consulta.db).por_prestamo(prestamo_id)
        elif tipo is not None:
            filas = ObservacionesSombraV3Repo(self._consulta.db).por_tipo(tipo)
        else:
            filas = self._consulta.db.consultar(
                """SELECT *
                   FROM observaciones_sombra_v3
                   ORDER BY id DESC
                   LIMIT ?""",
                (limite,),
            )

        filas = list(filas)
        filas = filas[-limite:] if prestamo_id is not None or tipo is not None else filas
        filas.reverse()
        return tuple(dict(fila) for fila in filas)


def obtener_metricas_sombra_v3(db, prestamo_id: int | None = None) -> MetricasSombraV3:
    return ServicioMetricasSombraV3(db).obtener(prestamo_id)
