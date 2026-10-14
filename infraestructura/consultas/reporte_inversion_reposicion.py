"""Adaptador SQLite de solo lectura para informes de reposición e inversión."""

from __future__ import annotations

from decimal import Decimal

from aplicacion.puertos.reporte_inversion_reposicion import (
    AporteReposicionLectura,
    ConsultaReporteInversionReposicion,
    FlujoInversionReposicionLectura,
    PlanReposicionLectura,
    ResumenRendimientoInversionLectura,
    TipoConteoReporteReposicion,
    ValoracionInversionReposicionLectura,
    VersionPlanReposicionLectura,
)
from infraestructura.repositorios import PlanesReposicionRepo


_TABLAS_CONTEO = {
    "aportes": "aportes_reposicion",
    "flujos": "flujos_inversion_reposicion",
    "valuaciones": "valuaciones_inversion_reposicion",
}


class ReporteInversionReposicionSQLiteQuery:
    """Conecta el puerto de informe al repositorio local existente."""

    def __init__(self, db) -> None:
        self._db = db
        self._repo = PlanesReposicionRepo(db)

    def obtener_plan(self, plan_id: int) -> PlanReposicionLectura | None:
        return self._repo.obtener_plan(plan_id)

    def obtener_version(
        self, plan_id: int, numero_version: int
    ) -> VersionPlanReposicionLectura | None:
        return self._repo.obtener_version(plan_id, numero_version)

    def verificar_version(self, version: VersionPlanReposicionLectura) -> bool:
        return self._repo.verificar_version(version)

    def contar_registros(
        self, tipo: TipoConteoReporteReposicion, plan_id: int
    ) -> int:
        """Cuenta solo categorías permitidas; los nombres SQL nunca vienen de entrada."""
        tabla = _TABLAS_CONTEO.get(tipo)
        if tabla is None:
            raise ValueError("Tipo de conteo no admitido para el informe")
        fila = self._db.consultar_uno(
            f"SELECT COUNT(*) AS cantidad FROM {tabla} WHERE plan_id = ?",
            (plan_id,),
        )
        return int(fila["cantidad"])

    def listar_aportes(
        self, plan_id: int, limite: int
    ) -> tuple[AporteReposicionLectura, ...]:
        return tuple(self._repo.listar_aportes(plan_id, limite=limite))

    def obtener_aporte(self, aporte_id: int) -> AporteReposicionLectura | None:
        return self._repo.obtener_aporte(aporte_id)

    def verificar_aporte(self, aporte: AporteReposicionLectura) -> bool:
        return self._repo.verificar_aporte(aporte)

    def listar_flujos_inversion(
        self, plan_id: int, limite: int
    ) -> tuple[FlujoInversionReposicionLectura, ...]:
        return tuple(self._repo.listar_flujos_inversion(plan_id, limite=limite))

    def listar_valuaciones_inversion(
        self, plan_id: int, limite: int
    ) -> tuple[ValoracionInversionReposicionLectura, ...]:
        return tuple(self._repo.listar_valuaciones_inversion(plan_id, limite=limite))

    def resumen_rendimiento_inversion(
        self, plan_id: int
    ) -> ResumenRendimientoInversionLectura:
        return self._repo.resumen_rendimiento_inversion(plan_id)


__all__ = ["ReporteInversionReposicionSQLiteQuery"]
