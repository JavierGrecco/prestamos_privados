"""Abstracción de identidad de sesión.

La aplicación consume una identidad ya resuelta por un proveedor externo.
El proveedor local incluido aquí existe solo para desarrollo/uso local y se
marca explícitamente como no autenticado.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol


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


class ProveedorIdentidad(Protocol):
    """Contrato mínimo que debe cumplir un proveedor de identidad."""

    def obtener_identidad(self) -> IdentidadSesion:
        """Devuelve la identidad resuelta para la sesión actual."""


class ProveedorIdentidadLocal:
    """Proveedor de desarrollo: identidad declarada, no autenticada."""

    VARIABLE_ACTOR = "PRESTAMOS_OPERADOR"
    VARIABLE_ROL = "PRESTAMOS_ROL_LOCAL"

    def obtener_identidad(self) -> IdentidadSesion:
        actor = os.environ.get(self.VARIABLE_ACTOR, "admin").strip() or "admin"
        from aplicacion.seguridad.capacidades import rol_local_desde_entorno

        return IdentidadSesion(
            subject=f"local:{actor}",
            nombre=actor,
            proveedor="LOCAL",
            autenticada=False,
            roles=rol_local_desde_entorno(
                os.environ.get(self.VARIABLE_ROL)
            ),
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



class ProveedorIdentidadUsuarioLocal:
    """Resuelve una cuenta local ya autenticada por ServicioUsuariosLocales.

    La contraseña nunca forma parte de la identidad. El rol proviene de la
    cuenta persistida y no de un campo editable en la interfaz ni de una
    variable de entorno.
    """

    def __init__(
        self,
        *,
        usuario_id: int,
        username: str,
        nombre: str,
        rol: str,
    ) -> None:
        if usuario_id <= 0:
            raise ValueError("El ID de usuario debe ser positivo.")
        rol_normalizado = rol.strip().upper()
        if rol_normalizado not in {"ADMIN", "OPERADOR", "LECTURA"}:
            raise ValueError("El rol de la cuenta local no es válido.")
        self._usuario_id = usuario_id
        self._username = username.strip().lower()
        self._nombre = nombre.strip()
        self._rol = rol_normalizado

    def obtener_identidad(self) -> IdentidadSesion:
        """Devuelve la identidad autenticada asociada a la cuenta local."""
        if not self._username or not self._nombre:
            raise ValueError("La cuenta local necesita usuario y nombre.")
        return IdentidadSesion(
            subject=f"local-db:{self._usuario_id}",
            nombre=self._nombre,
            proveedor="LOCAL_DB",
            autenticada=True,
            roles=frozenset({self._rol}),
        )
