"""Read model de métricas de adopción para SOMBRA V3.

No recalcula resultados financieros y no modifica la base.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConteoSombraV3:
    etiqueta: str
    cantidad: int


@dataclass(frozen=True)
class MetricasSombraV3:
    total_observaciones: int
    divergencias: int
    errores_sombra: int
    prestamos_con_observaciones: int
    fingerprints_distintos: int
    primera_observacion: str | None
    ultima_observacion: str | None
    por_tipo: tuple[ConteoSombraV3, ...]
    por_prestamo: tuple[ConteoSombraV3, ...]
    por_fingerprint: tuple[ConteoSombraV3, ...]

    @property
    def observaciones_con_error(self) -> int:
        return self.errores_sombra

    @property
    def hay_observaciones(self) -> bool:
        return self.total_observaciones > 0


class MetricasSombraV3Query:
    """Consulta agregada, determinista y de solo lectura."""

    def __init__(self, db) -> None:
        self.db = db

    def obtener(self, prestamo_id: int | None = None) -> MetricasSombraV3:
        filtro = ""
        params: tuple[Any, ...] = ()
        if prestamo_id is not None:
            if prestamo_id <= 0:
                raise ValueError("prestamo_id debe ser positivo")
            filtro = " WHERE prestamo_id = ? "
            params = (prestamo_id,)

        fila = self.db.consultar_uno(
            f"""SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN tipo = 'DIVERGENCIA' THEN 1 ELSE 0 END) AS divergencias,
                    SUM(CASE WHEN tipo = 'ERROR_SOMBRA' THEN 1 ELSE 0 END) AS errores,
                    COUNT(DISTINCT prestamo_id) AS prestamos,
                    COUNT(DISTINCT fingerprint) AS fingerprints,
                    MIN(creado_en) AS primera,
                    MAX(creado_en) AS ultima
                FROM observaciones_sombra_v3{filtro}""",
            params,
        )

        total = int(fila["total"] or 0)
        divergencias = int(fila["divergencias"] or 0)
        errores = int(fila["errores"] or 0)

        return MetricasSombraV3(
            total_observaciones=total,
            divergencias=divergencias,
            errores_sombra=errores,
            prestamos_con_observaciones=int(fila["prestamos"] or 0),
            fingerprints_distintos=int(fila["fingerprints"] or 0),
            primera_observacion=None if fila["primera"] is None else str(fila["primera"]),
            ultima_observacion=None if fila["ultima"] is None else str(fila["ultima"]),
            por_tipo=self._conteos("tipo", prestamo_id),
            por_prestamo=self._conteos("prestamo_id", prestamo_id),
            por_fingerprint=self._conteos("fingerprint", prestamo_id),
        )

    def _conteos(
        self,
        columna: str,
        prestamo_id: int | None,
    ) -> tuple[ConteoSombraV3, ...]:
        filtro = ""
        params: tuple[Any, ...] = ()
        if prestamo_id is not None:
            filtro = " WHERE prestamo_id = ? "
            params = (prestamo_id,)

        filas = self.db.consultar(
            f"""SELECT {columna} AS etiqueta, COUNT(*) AS cantidad
                FROM observaciones_sombra_v3
                {filtro}
                GROUP BY {columna}
                ORDER BY cantidad DESC, {columna} ASC""",
            params,
        )
        return tuple(
            ConteoSombraV3(
                etiqueta=str(f["etiqueta"]),
                cantidad=int(f["cantidad"]),
            )
            for f in filas
        )


def obtener_metricas_sombra_v3(db, prestamo_id: int | None = None) -> MetricasSombraV3:
    return MetricasSombraV3Query(db).obtener(prestamo_id)
