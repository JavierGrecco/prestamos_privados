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
RegistroReposicionCorregible = (
    AporteReposicionLectura
    | FlujoInversionReposicionLectura
    | ValoracionInversionReposicionLectura
)


class CatalogoCorreccionesReposicion(Protocol):
    """Lecturas del plan y sus registros, delegadas a un adaptador."""

    def listar_planes(
        self, limite: int, *, solo_activos: bool = False
    ) -> Sequence[PlanReposicionLectura]: ...

    def obtener_plan(self, plan_id: int) -> PlanReposicionLectura | None: ...

    def listar_aportes(
        self, plan_id: int, limite: int
    ) -> Sequence[AporteReposicionLectura]: ...

    def obtener_aporte(self, aporte_id: int) -> AporteReposicionLectura | None: ...

    def verificar_aporte(self, aporte: AporteReposicionLectura) -> bool: ...

    def listar_flujos_inversion(
        self, plan_id: int, limite: int
    ) -> Sequence[FlujoInversionReposicionLectura]: ...

    def obtener_flujo_inversion(
        self, flujo_id: int
    ) -> FlujoInversionReposicionLectura | None: ...

    def verificar_flujo_inversion(
        self, flujo: FlujoInversionReposicionLectura
    ) -> bool: ...

    def listar_valuaciones_inversion(
        self, plan_id: int, limite: int
    ) -> Sequence[ValoracionInversionReposicionLectura]: ...

    def obtener_valoracion_inversion(
        self, valuacion_id: int
    ) -> ValoracionInversionReposicionLectura | None: ...

    def verificar_valoracion_inversion(
        self, valuacion: ValoracionInversionReposicionLectura
    ) -> bool: ...


__all__ = [
    "TipoRegistroCorreccion",
    "RegistroReposicionCorregible",
    "CatalogoCorreccionesReposicion",
]
