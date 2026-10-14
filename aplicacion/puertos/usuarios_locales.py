"""Contratos públicos para la gestión de cuentas locales.

La aplicación define qué operaciones necesita. La infraestructura decide cómo
persistirlas y agrupa sus escrituras en una unidad de trabajo atómica.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ContextManager, Protocol


@dataclass(frozen=True)
class UsuarioApp:
    """Datos seguros de una cuenta; nunca incluye ni expone el hash de contraseña."""

    id: int
    username: str
    nombre: str
    rol: str
    activo: bool
    intentos_login_fallidos: int
    bloqueado_hasta: str | None
    ultimo_acceso_en: str | None
    creado_en: str
    actualizado_en: str
    revision_sesion: int
    persona_id: int | None = None


class PersonaVinculable(Protocol):
    """Campos de persona que necesita la administración de cuentas locales."""

    id: int
    nombre: str
    apellido: str
    documento: str | None
    estado: str

    @property
    def nombre_completo(self) -> str: ...


class RepositorioUsuariosLocales(Protocol):
    """Lecturas y cambios de cuentas, sin detalles del motor de base de datos."""

    def cantidad(self) -> int: ...

    def listar(self) -> tuple[UsuarioApp, ...]: ...

    def obtener(self, usuario_id: int) -> UsuarioApp | None: ...

    def por_username(self, username: str) -> tuple[UsuarioApp, str] | None: ...

    def crear(
        self,
        *,
        username: str,
        nombre: str,
        rol: str,
        password_hash: str,
        ahora: str,
        persona_id: int | None = None,
    ) -> int: ...

    def actualizar_perfil(
        self,
        usuario_id: int,
        *,
        nombre: str,
        rol: str,
        activo: bool,
        persona_id: int | None,
        ahora: str,
    ) -> None: ...

    def cambiar_password(
        self, usuario_id: int, password_hash: str, ahora: str
    ) -> None: ...

    def registrar_fallo_login(
        self,
        usuario_id: int,
        *,
        intentos: int,
        bloqueado_hasta: str | None,
        ahora: str,
    ) -> None: ...

    def registrar_login_correcto(self, usuario_id: int, ahora: str) -> None: ...

    def administradores_activos(self) -> int: ...


class ConsultaPersonasUsuariosLocales(Protocol):
    """Lecturas mínimas de personas para vínculos opcionales de cuentas."""

    def obtener(self, persona_id: int) -> PersonaVinculable | None: ...

    def listar(
        self, estado: str | None = None
    ) -> Sequence[PersonaVinculable]: ...


class RegistroAuditoriaUsuariosLocales(Protocol):
    """Registro auditable de operaciones administrativas sobre cuentas."""

    def registrar(
        self,
        *,
        usuario: str,
        operacion: str,
        entidad: str,
        entidad_id: int | None = None,
        correlacion_id: str | None = None,
        datos_anteriores: dict | None = None,
        datos_nuevos: dict | None = None,
        motivo: str | None = None,
    ) -> int: ...


class UnidadTrabajoUsuariosLocales(Protocol):
    """Mantiene atómica una operación de cuenta y su auditoría."""

    def transaccion(self) -> ContextManager[None]: ...


class NombreUsuarioDuplicado(Exception):
    """El nombre de usuario ya está ocupado por otra cuenta."""


__all__ = [
    "UsuarioApp",
    "PersonaVinculable",
    "RepositorioUsuariosLocales",
    "ConsultaPersonasUsuariosLocales",
    "RegistroAuditoriaUsuariosLocales",
    "UnidadTrabajoUsuariosLocales",
    "NombreUsuarioDuplicado",
]
