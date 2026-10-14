"""Contratos de lectura para elegir registros que admiten una propuesta de corrección.

Los contratos exponen los datos necesarios para la pantalla, sin revelar SQLite
ni obligar a la aplicación a conocer el repositorio que los obtiene.
"""
from __future__ import annotations

from typing import Literal, Protocol, Sequence

from aplicacion.puertos.reporte_inversion_reposicion import (
    AporteReposicionLectura,
    FlujoInversionReposicionLectura,
    PlanReposicionLectura,
    ValoracionInversionReposicionLectura,
)

TipoRegistroCorreccion = Literal[
    "APORTE_REPOSICION",
    "FLUJO_INVERSION_REPOSICION",
    "VALUACION_INVERSION_REPOSICION",
]


class AporteReposicionCorregible(AporteReposicionLectura, Protocol):
    """Campos de un aporte que necesita revisar el formulario, incluido su snapshot."""

    snapshot_json: str | None


class FlujoInversionReposicionCorregible(FlujoInversionReposicionLectura, Protocol):
    """Campos de un flujo que necesita revisar el formulario, incluido su snapshot."""

    snapshot_json: str | None


class ValoracionInversionReposicionCorregible(ValoracionInversionReposicionLectura, Protocol):
    """Campos de una valuación que necesita revisar el formulario, incluido su snapshot."""

    snapshot_json: str | None


RegistroReposicionCorregible = (
    AporteReposicionCorregible
    | FlujoInversionReposicionCorregible
    | ValoracionInversionReposicionCorregible
)


class CatalogoCorreccionesReposicion(Protocol):
    """Lecturas del plan y sus registros, delegadas a un adaptador."""

    def listar_planes(
        self, limite: int, *, solo_activos: bool = False
    ) -> Sequence[PlanReposicionLectura]: ...

    def obtener_plan(self, plan_id: int) -> PlanReposicionLectura | None: ...

    def listar_aportes(
        self, plan_id: int, limite: int
    ) -> Sequence[AporteReposicionCorregible]: ...

    def obtener_aporte(self, aporte_id: int) -> AporteReposicionCorregible | None: ...

    def verificar_aporte(self, aporte: AporteReposicionCorregible) -> bool: ...

    def listar_flujos_inversion(
        self, plan_id: int, limite: int
    ) -> Sequence[FlujoInversionReposicionCorregible]: ...

    def obtener_flujo_inversion(
        self, flujo_id: int
    ) -> FlujoInversionReposicionCorregible | None: ...

    def verificar_flujo_inversion(
        self, flujo: FlujoInversionReposicionCorregible
    ) -> bool: ...

    def listar_valuaciones_inversion(
        self, plan_id: int, limite: int
    ) -> Sequence[ValoracionInversionReposicionCorregible]: ...

    def obtener_valoracion_inversion(
        self, valuacion_id: int
    ) -> ValoracionInversionReposicionCorregible | None: ...

    def verificar_valoracion_inversion(
        self, valuacion: ValoracionInversionReposicionCorregible
    ) -> bool: ...


__all__ = [
    "TipoRegistroCorreccion",
    "AporteReposicionCorregible",
    "FlujoInversionReposicionCorregible",
    "ValoracionInversionReposicionCorregible",
    "RegistroReposicionCorregible",
    "CatalogoCorreccionesReposicion",
]
