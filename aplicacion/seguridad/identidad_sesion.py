"""Modelo de datos de identidad para una sesión.

Este contrato pequeño se mantiene separado del proveedor de identidad y de la
política de permisos para que ambas capacidades puedan depender de él sin
importarse entre sí.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class IdentidadSesion:
    """Identidad que una sesión puede presentar a la aplicación."""

    subject: str
    nombre: str
    proveedor: str
    autenticada: bool
    roles: frozenset[str] = field(default_factory=frozenset)

    @property
    def disponible(self) -> bool:
        return bool(self.subject.strip())
