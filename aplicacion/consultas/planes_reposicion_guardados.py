"""Consulta de lectura para planes guardados en el simulador de carencia.

Centraliza la selección de planes, la verificación de versiones y la lectura
segura del snapshot. No modifica los datos ni vuelve a calcular el escenario.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal

from dominio.excepciones import ErrorValidacion
from aplicacion.puertos.planes_reposicion_guardados import (
    FuentePlanesReposicionGuardados,
)


@dataclass(frozen=True)
class PlanReposicionGuardado:
    """Datos que la UI necesita para seleccionar y titular un plan."""

    id: int
    nombre: str
    tipo_plan: str
    capital_original_ars: Decimal
    estado: str
    ultima_version: int


@dataclass(frozen=True)
class VersionReposicionGuardada:
    """Una versión y el resultado de comprobar su integridad y contenido."""

    id: int
    plan_id: int
    numero_version: int
    snapshot_sha256: str
    creado_por: str
    creado_en: str
    integridad_valida: bool
    contenido_valido: bool
    contenido: dict | None


class ConsultaPlanesReposicionGuardados:
    """Expone lecturas tipadas sin entregar repositorios a la interfaz."""

    def __init__(self, fuente: FuentePlanesReposicionGuardados) -> None:
        self._fuente = fuente

    def listar_planes(
        self, limite: int = 30, *, solo_activos: bool = False
    ) -> tuple[PlanReposicionGuardado, ...]:
        if not isinstance(limite, int) or isinstance(limite, bool) or limite <= 0:
            raise ErrorValidacion("El límite de planes debe ser un entero positivo")
        return tuple(
            _plan_a_dto(plan)
            for plan in self._fuente.listar_planes(
                limite=limite, solo_activos=solo_activos
            )
        )

    def obtener_plan(self, plan_id: int) -> PlanReposicionGuardado | None:
        _validar_id(plan_id, "plan")
        plan = self._fuente.obtener_plan(plan_id)
        return None if plan is None else _plan_a_dto(plan)

    def listar_versiones(self, plan_id: int) -> tuple[int, ...]:
        """Lista solo los números de versión para que la UI arme el selector."""
        _validar_id(plan_id, "plan")
        return tuple(
            int(version.numero_version)
            for version in self._fuente.listar_versiones(plan_id)
        )

    def obtener_version(
        self, plan_id: int, numero_version: int
    ) -> VersionReposicionGuardada | None:
        _validar_id(plan_id, "plan")
        _validar_id(numero_version, "versión")
        version = self._fuente.obtener_version(plan_id, numero_version)
        if version is None:
            return None

        integridad_valida = self._fuente.verificar_version(version)
        contenido = None
        contenido_valido = False
        if integridad_valida:
            try:
                decodificado = json.loads(version.snapshot_json or "{}")
            except (TypeError, json.JSONDecodeError):
                decodificado = None
            if isinstance(decodificado, dict):
                contenido = decodificado
                contenido_valido = True

        return _version_a_dto(
            version,
            integridad_valida=integridad_valida,
            contenido_valido=contenido_valido,
            contenido=contenido,
        )


def _validar_id(valor: int, etiqueta: str) -> None:
    if not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
        raise ErrorValidacion(f"El identificador de {etiqueta} no es válido")


def _plan_a_dto(plan) -> PlanReposicionGuardado:
    return PlanReposicionGuardado(
        id=int(plan.id),
        nombre=str(plan.nombre),
        tipo_plan=str(plan.tipo_plan),
        capital_original_ars=plan.capital_original_ars,
        estado=str(plan.estado),
        ultima_version=int(plan.ultima_version),
    )


def _version_a_dto(
    version,
    *,
    integridad_valida: bool,
    contenido_valido: bool,
    contenido: dict | None,
) -> VersionReposicionGuardada:
    return VersionReposicionGuardada(
        id=int(version.id),
        plan_id=int(version.plan_id),
        numero_version=int(version.numero_version),
        snapshot_sha256=str(version.snapshot_sha256),
        creado_por=str(version.creado_por),
        creado_en=str(version.creado_en),
        integridad_valida=integridad_valida,
        contenido_valido=contenido_valido,
        contenido=contenido,
    )


__all__ = [
    "ConsultaPlanesReposicionGuardados",
    "PlanReposicionGuardado",
    "VersionReposicionGuardada",
]
