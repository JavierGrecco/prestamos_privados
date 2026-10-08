"""
Sistema de migraciones de base de datos.

Cada migración es un archivo Python que sabe cómo aplicar un cambio
al schema (crear tablas, agregar columnas, crear índices). El gestor
las aplica en orden, una sola vez cada una, y registra cuáles ya se
aplicaron en la tabla `migraciones`.

¿Por qué migraciones y no simplemente crear todas las tablas de una?

Porque el schema va a evolucionar. La v1 tiene ciertas tablas, la v2
agrega otras, la v3 modifica alguna columna. Si no hay un sistema
formal, cada cambio se vuelve un caos de "¿en qué versión estás?".

Con migraciones:
  - Cada cambio es un archivo con un número.
  - Se aplican en orden estricto.
  - Nunca se aplica dos veces la misma.
  - Se puede saber en qué versión está una base.
  - Si algo falla, se revierte.
"""
from .gestor import (
    EstadoMigraciones,
    MigracionPlaneada,
    aplicar_migraciones,
    inspeccionar_estado_migraciones,
    listar_migraciones_planeadas,
    version_actual,
    version_destino_migraciones,
)

__all__ = [
    "EstadoMigraciones",
    "MigracionPlaneada",
    "aplicar_migraciones",
    "inspeccionar_estado_migraciones",
    "listar_migraciones_planeadas",
    "version_actual",
    "version_destino_migraciones",
]