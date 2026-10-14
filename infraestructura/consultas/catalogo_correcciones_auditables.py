"""Adaptador SQLite de solo lectura para el catálogo de correcciones auditables."""

from __future__ import annotations

from aplicacion.puertos.catalogo_correcciones_auditables import (
    AporteReposicionLectura,
    FlujoInversionReposicionLectura,
    PlanReposicionLectura,
    ValoracionInversionReposicionLectura,
)
from infraestructura.repositorios import PlanesReposicionRepo


class CatalogoCorreccionesAuditablesSQLiteQuery:
    """Traduce el contrato de lectura al repositorio SQLite existente."""

    def __init__(self, db) -> None:
        self._repo = PlanesReposicionRepo(db)

    def listar_planes(
        self, limite: int, *, solo_activos: bool = False
    ) -> tuple[PlanReposicionLectura, ...]:
        return tuple(self._repo.listar_planes(limite=limite, solo_activos=solo_activos))

    def obtener_plan(self, plan_id: int) -> PlanReposicionLectura | None:
        return self._repo.obtener_plan(plan_id)

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

    def obtener_flujo_inversion(
        self, flujo_id: int
    ) -> FlujoInversionReposicionLectura | None:
        return self._repo.obtener_flujo_inversion(flujo_id)

    def verificar_flujo_inversion(
        self, flujo: FlujoInversionReposicionLectura
    ) -> bool:
        return self._repo.verificar_flujo_inversion(flujo)

    def listar_valuaciones_inversion(
        self, plan_id: int, limite: int
    ) -> tuple[ValoracionInversionReposicionLectura, ...]:
        return tuple(self._repo.listar_valuaciones_inversion(plan_id, limite=limite))

    def obtener_valoracion_inversion(
        self, valuacion_id: int
    ) -> ValoracionInversionReposicionLectura | None:
        return self._repo.obtener_valoracion_inversion(valuacion_id)

    def verificar_valoracion_inversion(
        self, valuacion: ValoracionInversionReposicionLectura
    ) -> bool:
        return self._repo.verificar_valoracion_inversion(valuacion)


__all__ = ["CatalogoCorreccionesAuditablesSQLiteQuery"]
