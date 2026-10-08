"""
Capa de infraestructura del sistema.

Esta capa adapta el mundo exterior (SQLite, archivos, APIs externas)
al lenguaje del dominio. Ninguna parte del dominio sabe que existe
esta capa.
"""
from .db import BaseDatos, conectar
from .backup import (
    ResultadoIntegridad,
    ResultadoBackup,
    ResultadoRestore,
    verificar_integridad_sqlite,
    crear_backup_verificado,
    verificar_backup,
    restaurar_backup_verificado,
)
from .excepciones import (
    ErrorBaseDatos,
    ErrorConexion,
    ErrorIntegridad,
    ErrorTransaccion,
    ErrorMigracion,
    ErrorBackup,
    ErrorRestore,
)

__all__ = [
    "BaseDatos",
    "conectar",
    "ErrorBaseDatos",
    "ErrorConexion",
    "ErrorIntegridad",
    "ErrorTransaccion",
    "ErrorMigracion",
    "ResultadoIntegridad",
    "ResultadoBackup",
    "ResultadoRestore",
    "verificar_integridad_sqlite",
    "crear_backup_verificado",
    "verificar_backup",
    "restaurar_backup_verificado",
    "ErrorBackup",
    "ErrorRestore",
]