"""Repositorio para cuentas que acceden a la aplicación.

Estas cuentas no son las personas del negocio: una cuenta de acceso puede no
ser inversor/deudor, y una persona puede no tener permiso para iniciar sesión.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..db import BaseDatos
from .base import RepositorioBase


@dataclass(frozen=True)
class UsuarioApp:
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


class UsuarioAppRepo(RepositorioBase):
    """Acceso a la tabla usuarios_app sin exponer hashes en modelos públicos."""

    def __init__(self, db: BaseDatos):
        super().__init__(db)

    def cantidad(self) -> int:
        fila = self.db.consultar_uno("SELECT COUNT(*) AS n FROM usuarios_app")
        return int(fila["n"])

    def obtener(self, usuario_id: int) -> UsuarioApp | None:
        fila = self.db.consultar_uno(
            "SELECT * FROM usuarios_app WHERE id = ?",
            (usuario_id,),
        )
        return self._modelo(fila) if fila else None

    def por_username(
        self, username: str
    ) -> tuple[UsuarioApp, str] | None:
        fila = self.db.consultar_uno(
            "SELECT * FROM usuarios_app WHERE username = ?",
            (username,),
        )
        if fila is None:
            return None
        return self._modelo(fila), str(fila["password_hash"])

    def listar(self) -> tuple[UsuarioApp, ...]:
        filas = self.db.consultar(
            """
            SELECT * FROM usuarios_app
            ORDER BY activo DESC, username COLLATE NOCASE, id
            """
        )
        return tuple(self._modelo(fila) for fila in filas)

    def crear(
        self,
        *,
        username: str,
        nombre: str,
        rol: str,
        password_hash: str,
        ahora: str,
        persona_id: int | None = None,
    ) -> int:
        self.db.ejecutar(
            """
            INSERT INTO usuarios_app
                (username, nombre, rol, password_hash, activo,
                 intentos_login_fallidos, bloqueado_hasta, ultimo_acceso_en,
                 persona_id, creado_en, actualizado_en)
            VALUES (?, ?, ?, ?, 1, 0, NULL, NULL, ?, ?, ?)
            """,
            (username, nombre, rol, password_hash, persona_id, ahora, ahora),
        )
        return self.db.ultimo_id_insertado()

    def actualizar_perfil(
        self,
        usuario_id: int,
        *,
        nombre: str,
        rol: str,
        activo: bool,
        persona_id: int | None,
        ahora: str,
    ) -> None:
        self.db.ejecutar(
            """
            UPDATE usuarios_app
            SET nombre = ?, rol = ?, activo = ?, persona_id = ?,
                actualizado_en = ?,
                revision_sesion = revision_sesion + CASE
                    WHEN rol <> ? OR activo <> ? OR persona_id IS NOT ?
                    THEN 1 ELSE 0
                END
            WHERE id = ?
            """,
            (
                nombre,
                rol,
                int(activo),
                persona_id,
                ahora,
                rol,
                int(activo),
                persona_id,
                usuario_id,
            ),
        )

    def cambiar_password(
        self, usuario_id: int, password_hash: str, ahora: str
    ) -> None:
        self.db.ejecutar(
            """
            UPDATE usuarios_app
            SET password_hash = ?, intentos_login_fallidos = 0,
                bloqueado_hasta = NULL, actualizado_en = ?,
                revision_sesion = revision_sesion + 1
            WHERE id = ?
            """,
            (password_hash, ahora, usuario_id),
        )

    def registrar_fallo_login(
        self,
        usuario_id: int,
        *,
        intentos: int,
        bloqueado_hasta: str | None,
        ahora: str,
    ) -> None:
        self.db.ejecutar(
            """
            UPDATE usuarios_app
            SET intentos_login_fallidos = ?, bloqueado_hasta = ?,
                actualizado_en = ?
            WHERE id = ?
            """,
            (intentos, bloqueado_hasta, ahora, usuario_id),
        )

    def registrar_login_correcto(self, usuario_id: int, ahora: str) -> None:
        self.db.ejecutar(
            """
            UPDATE usuarios_app
            SET intentos_login_fallidos = 0, bloqueado_hasta = NULL,
                ultimo_acceso_en = ?, actualizado_en = ?
            WHERE id = ?
            """,
            (ahora, ahora, usuario_id),
        )

    def administradores_activos(self) -> int:
        fila = self.db.consultar_uno(
            """
            SELECT COUNT(*) AS n
            FROM usuarios_app
            WHERE rol = 'ADMIN' AND activo = 1
            """
        )
        return int(fila["n"])

    @staticmethod
    def _modelo(fila) -> UsuarioApp:
        return UsuarioApp(
            id=int(fila["id"]),
            username=str(fila["username"]),
            nombre=str(fila["nombre"]),
            rol=str(fila["rol"]),
            activo=bool(fila["activo"]),
            intentos_login_fallidos=int(fila["intentos_login_fallidos"]),
            bloqueado_hasta=fila["bloqueado_hasta"],
            ultimo_acceso_en=fila["ultimo_acceso_en"],
            creado_en=str(fila["creado_en"]),
            actualizado_en=str(fila["actualizado_en"]),
            revision_sesion=int(fila["revision_sesion"]),
            persona_id=(
                int(fila["persona_id"])
                if fila["persona_id"] is not None
                else None
            ),
        )
