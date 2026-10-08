"""Abstracción de identidad de sesión.

La aplicación consume una identidad ya resuelta por un proveedor externo.
El proveedor local incluido aquí existe solo para desarrollo/uso local y se
marca explícitamente como no autenticado.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class IdentidadSesion:
    """Identidad que una sesión puede presentar a la aplicación."""

    subject: str
    nombre: str
    proveedor: str
    autenticada: bool

    @property
    def disponible(self) -> bool:
        return bool(self.subject.strip())


class ProveedorIdentidad(Protocol):
    """Contrato mínimo que debe cumplir un proveedor de identidad."""

    def obtener_identidad(self) -> IdentidadSesion:
        """Devuelve la identidad resuelta para la sesión actual."""


class ProveedorIdentidadLocal:
    """Proveedor de desarrollo: identidad declarada, no autenticada."""

    VARIABLE_ACTOR = "PRESTAMOS_OPERADOR"

    def obtener_identidad(self) -> IdentidadSesion:
        actor = os.environ.get(self.VARIABLE_ACTOR, "admin").strip() or "admin"
        return IdentidadSesion(
            subject=f"local:{actor}",
            nombre=actor,
            proveedor="LOCAL",
            autenticada=False,
        )


def identidad_desde_proveedor(
    proveedor: ProveedorIdentidad,
) -> IdentidadSesion:
    """Punto de entrada para cambiar de proveedor sin tocar la UI."""
    identidad = proveedor.obtener_identidad()
    if not isinstance(identidad, IdentidadSesion):
        raise TypeError(
            "El proveedor de identidad debe devolver IdentidadSesion"
        )
    if not identidad.subject.strip():
        raise ValueError("La identidad de sesión debe tener un subject")
    return identidad


def descripcion_identidad(identidad: IdentidadSesion) -> str:
    """Texto breve para mostrar cómo se obtuvo la identidad."""
    if identidad.autenticada:
        return (
            f"Sesión autenticada por {identidad.proveedor}: "
            f"{identidad.nombre}"
        )
    return (
        f"Sesión sin autenticación real ({identidad.proveedor}): "
        f"{identidad.nombre}"
    )
