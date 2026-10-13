"""Contratos de operaciones operativas sobre bases y backups locales."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ResultadoIntegridadOperativa(Protocol):
    """Resultado estable de las verificaciones de integridad SQLite."""

    ruta: Path
    quick_check: tuple[str, ...]
    integrity_check: tuple[str, ...]
    foreign_key_errores: tuple[tuple[object, ...], ...]

    @property
    def ok(self) -> bool: ...


class ResultadoBackupOperativo(Protocol):
    """Evidencia verificable de un backup existente o recién creado."""

    ruta_backup: Path
    ruta_manifest: Path
    sha256: str
    bytes: int
    integridad: ResultadoIntegridadOperativa


class ResultadoRestoreOperativo(Protocol):
    """Evidencia de una restauración en una ruta distinta a la base activa."""

    ruta_restore: Path
    sha256: str
    bytes: int
    integridad: ResultadoIntegridadOperativa


class OperacionesBackup(Protocol):
    """Capacidades de backup e integridad que consume la UI operativa."""

    def verificar_integridad_sqlite(
        self, ruta: str | Path
    ) -> ResultadoIntegridadOperativa: ...

    def crear_backup_verificado(
        self, ruta_origen: str | Path, ruta_backup: str | Path
    ) -> ResultadoBackupOperativo: ...

    def verificar_backup(
        self, ruta_backup: str | Path
    ) -> ResultadoBackupOperativo: ...

    def restaurar_backup_verificado(
        self, ruta_backup: str | Path, ruta_restore: str | Path
    ) -> ResultadoRestoreOperativo: ...


__all__ = [
    "ResultadoIntegridadOperativa",
    "ResultadoBackupOperativo",
    "ResultadoRestoreOperativo",
    "OperacionesBackup",
]
