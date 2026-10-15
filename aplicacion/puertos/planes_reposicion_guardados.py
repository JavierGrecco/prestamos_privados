"""Contratos mínimos para consultar planes y versiones ya guardados.

La UI necesita mostrar metadatos y revisar el snapshot. No necesita saber
cómo se persisten los planes ni cómo se verifica su huella.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol, Sequence


class PlanReposicionGuardadoRecord(Protocol):
    """Campos del plan persistido que necesita la consulta."""

    id: int
    nombre: str
    tipo_plan: str
    fecha_desembolso: date
    capital_original_ars: Decimal
    estado: str
    ultima_version: int


class VersionReposicionGuardadaRecord(Protocol):
    """Campos de una versión guardada que se pueden verificar y mostrar."""

    id: int
    plan_id: int
    numero_version: int
    snapshot_sha256: str
    creado_por: str
    creado_en: str
    snapshot_json: str | None


class FuentePlanesReposicionGuardados(Protocol):
    """Lectura y verificación de versiones, sin acoplamiento a SQLite."""

    def listar_planes(
        self, limite: int = 30, *, solo_activos: bool = False
    ) -> Sequence[PlanReposicionGuardadoRecord]:
        """Devuelve planes en el orden de la persistencia."""

    def obtener_plan(
        self, plan_id: int
    ) -> PlanReposicionGuardadoRecord | None:
        """Obtiene los metadatos de un plan."""

    def listar_versiones(
        self, plan_id: int
    ) -> Sequence[VersionReposicionGuardadaRecord]:
        """Lista las versiones de un plan en su orden persistido."""

    def obtener_version(
        self, plan_id: int, numero_version: int
    ) -> VersionReposicionGuardadaRecord | None:
        """Obtiene una versión concreta, sin modificarla."""

    def verificar_version(
        self, version: VersionReposicionGuardadaRecord
    ) -> bool:
        """Comprueba la huella del snapshot almacenado."""


__all__ = [
    "FuentePlanesReposicionGuardados",
    "PlanReposicionGuardadoRecord",
    "VersionReposicionGuardadaRecord",
]
