"""Caso de uso para guardar el análisis calculado por el simulador.

Este servicio decide si se crea un plan nuevo o se agrega una versión. La
persistencia conserva la responsabilidad de validar el plan, guardar la
versión inmutable y ejecutar cada operación dentro de su transacción.
No calcula ni cambia los resultados financieros del snapshot.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from dominio.excepciones import ErrorValidacion
from aplicacion.puertos.guardar_analisis_reposicion import (
    RepositorioGuardadoAnalisis,
)


@dataclass(frozen=True)
class ResultadoGuardadoAnalisis:
    """Identifica el plan y la versión que se guardaron correctamente."""

    plan_id: int
    numero_version: int
    creado_nuevo: bool


class ServicioGuardarAnalisisReposicion:
    """Coordina el alta del plan o el guardado de una nueva versión."""

    def __init__(self, repositorio: RepositorioGuardadoAnalisis) -> None:
        self._repositorio = repositorio

    def guardar(
        self,
        *,
        plan_id_destino: int | None,
        nombre: str,
        tipo_plan: str,
        fecha_desembolso: date,
        capital_original_ars: Decimal,
        datos: dict[str, Any],
        creado_por: str,
    ) -> ResultadoGuardadoAnalisis:
        """Crea un plan nuevo cuando no hay destino; si no, guarda una versión.

        Los checks de estado, importes, integridad, snapshot y atomicidad se
        mantienen en el repositorio existente. Este caso de uso solo valida
        lo necesario para elegir correctamente la operación.
        """
        usuario = str(creado_por or "").strip()
        if not usuario:
            raise ErrorValidacion(
                "No se identificó la cuenta que guarda el análisis. "
                "Volvé a iniciar sesión."
            )

        if plan_id_destino is None:
            plan_id, numero_version = self._repositorio.crear_plan_con_snapshot(
                nombre=nombre or "",
                tipo_plan=tipo_plan,
                fecha_desembolso=fecha_desembolso,
                capital_original_ars=capital_original_ars,
                datos=datos,
                creado_por=usuario,
            )
            return ResultadoGuardadoAnalisis(
                plan_id=int(plan_id),
                numero_version=int(numero_version),
                creado_nuevo=True,
            )

        if (
            not isinstance(plan_id_destino, int)
            or isinstance(plan_id_destino, bool)
            or plan_id_destino <= 0
        ):
            raise ErrorValidacion(
                "Seleccioná un plan activo para guardar la nueva versión"
            )

        numero_version = self._repositorio.guardar_nueva_version(
            plan_id_destino,
            datos=datos,
            creado_por=usuario,
        )
        return ResultadoGuardadoAnalisis(
            plan_id=plan_id_destino,
            numero_version=int(numero_version),
            creado_nuevo=False,
        )


__all__ = ["ResultadoGuardadoAnalisis", "ServicioGuardarAnalisisReposicion"]
