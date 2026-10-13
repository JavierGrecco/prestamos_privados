"""Adaptador de las operaciones verificadas de backup e integridad SQLite."""

from __future__ import annotations

from pathlib import Path

from aplicacion.puertos.operaciones_backup import (
    ResultadoBackupOperativo,
    ResultadoIntegridadOperativa,
    ResultadoRestoreOperativo,
)
from infraestructura.backup import (
    crear_backup_verificado,
    restaurar_backup_verificado,
    verificar_backup,
    verificar_integridad_sqlite,
)


class OperacionesBackupSQLite:
    """Implementa el puerto operativo delegando en las rutinas verificadas."""

    def verificar_integridad_sqlite(
        self, ruta: str | Path
    ) -> ResultadoIntegridadOperativa:
        return verificar_integridad_sqlite(ruta)

    def crear_backup_verificado(
        self, ruta_origen: str | Path, ruta_backup: str | Path
    ) -> ResultadoBackupOperativo:
        return crear_backup_verificado(ruta_origen, ruta_backup)

    def verificar_backup(
        self, ruta_backup: str | Path
    ) -> ResultadoBackupOperativo:
        return verificar_backup(ruta_backup)

    def restaurar_backup_verificado(
        self, ruta_backup: str | Path, ruta_restore: str | Path
    ) -> ResultadoRestoreOperativo:
        return restaurar_backup_verificado(ruta_backup, ruta_restore)
