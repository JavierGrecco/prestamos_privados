"""Contratos públicos para registrar y consultar propuestas de corrección.

Las interfaces modelan operaciones del negocio. No exponen conexiones, filas
SQLite ni fragmentos SQL a los servicios de aplicación.
"""
from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class CorreccionAuditable:
    """Una propuesta inmutable registrada en la bitácora."""

    id: int
    entidad_tipo: str
    entidad_id: int
    hash_original: str
    snapshot_corregido_json: str
    hash_corregido: str
    motivo: str
    corregido_por: str
    corregido_en_utc: str
    clave_idempotencia: str
    correccion_anterior_id: int | None


@dataclass(frozen=True, slots=True)
class NuevaCorreccionAuditable:
    """Datos ya validados que se guardan dentro de una única transacción."""

    entidad_tipo: str
    entidad_id: int
    hash_original: str
    snapshot_corregido_json: str
    hash_corregido: str
    motivo: str
    corregido_por: str
    corregido_en_utc: str
    clave_idempotencia: str
    correccion_anterior_id: int | None


@dataclass(frozen=True, slots=True)
class SnapshotOriginalCorreccion:
    """Contenido y huella del registro original, devueltos como datos tipados."""

    snapshot_json: str
    snapshot_sha256: str


@dataclass(frozen=True, slots=True)
class UltimaCorreccionAuditable:
    """Referencia mínima para comprobar que una corrección continúa la cadena."""

    id: int
    hash_original: str


@dataclass(frozen=True, slots=True)
class ReferenciaCorreccionAuditable:
    """Identidad mínima usada para armar la lista de actividad reciente."""

    id: int
    entidad_tipo: str
    entidad_id: int


class UnidadTrabajoCorreccionesAuditables(Protocol):
    """Operaciones permitidas dentro de la transacción de escritura."""

    def obtener_por_clave(self, clave: str) -> CorreccionAuditable | None: ...

    def obtener_snapshot_original(
        self, entidad_tipo: str, entidad_id: int
    ) -> SnapshotOriginalCorreccion | None: ...

    def obtener_ultima_correccion(
        self, entidad_tipo: str, entidad_id: int
    ) -> UltimaCorreccionAuditable | None: ...

    def insertar(
        self, propuesta: NuevaCorreccionAuditable
    ) -> CorreccionAuditable: ...


class RepositorioCorreccionesAuditables(Protocol):
    """Lecturas y unidad de trabajo para el servicio de correcciones."""

    def transaccion(
        self,
    ) -> AbstractContextManager[UnidadTrabajoCorreccionesAuditables]: ...

    def listar_referencias_recientes(
        self, limite: int
    ) -> Sequence[ReferenciaCorreccionAuditable]: ...

    def obtener(self, propuesta_id: int) -> CorreccionAuditable | None: ...

    def listar_historial(
        self, entidad_tipo: str, entidad_id: int
    ) -> Sequence[CorreccionAuditable]: ...

    def obtener_snapshot_original(
        self, entidad_tipo: str, entidad_id: int
    ) -> SnapshotOriginalCorreccion | None: ...


__all__ = [
    "CorreccionAuditable",
    "NuevaCorreccionAuditable",
    "SnapshotOriginalCorreccion",
    "UltimaCorreccionAuditable",
    "ReferenciaCorreccionAuditable",
    "UnidadTrabajoCorreccionesAuditables",
    "RepositorioCorreccionesAuditables",
]
