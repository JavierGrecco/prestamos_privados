"""
Capa de infraestructura del sistema.

Esta capa adapta el mundo exterior (SQLite, archivos, APIs externas)
al lenguaje del dominio. Ninguna parte del dominio sabe que existe
esta capa.
"""
from .db import BaseDatos, conectar
from .excepciones import (
    ErrorBaseDatos,
    ErrorConexion,
    ErrorIntegridad,
    ErrorTransaccion,
    ErrorMigracion,
)

__all__ = [
    "BaseDatos",
    "conectar",
    "ErrorBaseDatos",
    "ErrorConexion",
    "ErrorIntegridad",
    "ErrorTransaccion",
    "ErrorMigracion",
]