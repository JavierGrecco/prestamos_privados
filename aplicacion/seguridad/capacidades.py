"""Autorización por roles y capacidades.

Este módulo no autentica identidades. Recibe una IdentidadSesion ya resuelta y
decide qué superficies puede consultar el usuario.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet

from aplicacion.seguridad.identidad import IdentidadSesion


CAP_VER_PERSONAS = "VER_PERSONAS"
CAP_VER_AUDITORIA = "VER_AUDITORIA"
CAP_VER_MOTOR_V3 = "VER_MOTOR_V3"
CAP_OPERAR = "OPERAR"
CAP_VER_PERSONA = "VER_PERSONA"
CAP_ADMINISTRAR_USUARIOS = "ADMINISTRAR_USUARIOS"
CAP_ADMINISTRAR_SISTEMA = "ADMINISTRAR_SISTEMA"
CAP_CONFIGURAR_MOTOR_V3 = "CONFIGURAR_MOTOR_V3"


@dataclass(frozen=True)
class DefinicionRol:
    nombre: str
    capacidades: FrozenSet[str]
    descripcion: str


ROLES: dict[str, DefinicionRol] = {
    "ADMIN": DefinicionRol(
        nombre="ADMIN",
        capacidades=frozenset(
            {
                CAP_VER_PERSONAS,
                CAP_VER_AUDITORIA,
                CAP_VER_MOTOR_V3,
                CAP_CONFIGURAR_MOTOR_V3,
                CAP_ADMINISTRAR_SISTEMA,
                CAP_OPERAR,
                CAP_VER_PERSONA,
                CAP_ADMINISTRAR_USUARIOS,
            }
        ),
        descripcion="Acceso completo y administración de cuentas de acceso.",
    ),
    "OPERADOR": DefinicionRol(
        nombre="OPERADOR",
        capacidades=frozenset(
            {
                CAP_VER_PERSONAS,
                CAP_OPERAR,
                CAP_VER_PERSONA,
            }
        ),
        descripcion="Puede operar y consultar, pero no acceder al control de Motor V3.",
    ),
    "LECTURA": DefinicionRol(
        nombre="LECTURA",
        capacidades=frozenset(
            {
                CAP_VER_PERSONA,
                CAP_VER_PERSONAS,
            }
        ),
        descripcion="Puede consultar personas y su información, sin operar.",
    ),
    "LOCAL_ADMIN": DefinicionRol(
        nombre="LOCAL_ADMIN",
        capacidades=frozenset(
            {
                CAP_VER_PERSONAS,
                CAP_VER_AUDITORIA,
                CAP_VER_MOTOR_V3,
                CAP_CONFIGURAR_MOTOR_V3,
                CAP_ADMINISTRAR_SISTEMA,
                CAP_OPERAR,
                CAP_VER_PERSONA,
                CAP_ADMINISTRAR_USUARIOS,
            }
        ),
        descripcion="Rol de compatibilidad para el modo local sin autenticación real.",
    ),
}


class PoliticaCapacidades:
    """Resuelve si una identidad posee una capacidad."""

    def __init__(self, roles: dict[str, DefinicionRol] | None = None) -> None:
        self._roles = roles or ROLES

    def capacidades_de(self, identidad: IdentidadSesion) -> frozenset[str]:
        resultado: set[str] = set()
        for rol in identidad.roles:
            definicion = self._roles.get(rol.upper())
            if definicion is not None:
                resultado.update(definicion.capacidades)
        return frozenset(resultado)

    def puede(
        self,
        identidad: IdentidadSesion,
        capacidad: str,
    ) -> bool:
        return capacidad in self.capacidades_de(identidad)

    def exigir(
        self,
        identidad: IdentidadSesion,
        capacidad: str,
    ) -> None:
        if not self.puede(identidad, capacidad):
            raise PermissionError(
                f"La identidad no tiene el permiso requerido: {capacidad}"
            )

    def descripcion_roles(self, identidad: IdentidadSesion) -> str:
        roles_validos = [
            rol
            for rol in identidad.roles
            if rol.upper() in self._roles
        ]
        return ", ".join(sorted(roles_validos)) or "Sin rol"


def rol_local_desde_entorno(valor: str | None) -> frozenset[str]:
    """Normaliza el rol usado solo por el proveedor local."""
    rol = (valor or "LOCAL_ADMIN").strip().upper()
    if rol not in ROLES:
        raise ValueError(
            f"Rol local desconocido: {rol}. Roles válidos: "
            + ", ".join(sorted(ROLES))
        )
    return frozenset({rol})
