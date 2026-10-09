"""Gestión y autenticación de cuentas locales de la aplicación.

Este servicio no autentica personas del negocio ni implementa registro público.
Es una primera etapa para despliegues locales, con roles RBAC y auditoría.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import re
import sqlite3
from collections.abc import Iterator
from uuid import uuid4

from aplicacion.seguridad.passwords_locales import (
    hash_password,
    validar_password,
    verificar_password,
)
from infraestructura.db import BaseDatos
from infraestructura.excepciones import ErrorTransaccion
from infraestructura.repositorios.auditoria import AuditoriaRepo
from infraestructura.repositorios.personas import PersonaRepo
from infraestructura.repositorios.usuarios_app import UsuarioApp, UsuarioAppRepo

ROLES_USUARIO_VALIDOS = ("ADMIN", "OPERADOR", "LECTURA")
MAX_INTENTOS_LOGIN = 5
DURACION_BLOQUEO = timedelta(minutes=10)
_USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,49}$")
_SIN_CAMBIO_PERSONA = object()


class ServicioUsuariosLocales:
    """Casos de uso para cuentas locales y autorización administrativa."""

    def __init__(self, db: BaseDatos):
        self.db = db
        self.usuarios = UsuarioAppRepo(db)
        self.personas = PersonaRepo(db)
        self.auditoria = AuditoriaRepo(db)

    @contextmanager
    def _transaccion(self) -> Iterator[None]:
        """Mantiene errores de negocio claros después del rollback.

        BaseDatos envuelve excepciones ajenas a la infraestructura en
        ErrorTransaccion. El servicio las desenvuelve solo para errores de
        validación/permisos conocidos; los fallos SQL conservan ErrorTransaccion.
        """
        try:
            with self.db.transaccion():
                yield
        except ErrorTransaccion as exc:
            causa = exc.__cause__
            if isinstance(causa, (ValueError, PermissionError)):
                raise causa
            raise

    def cantidad(self) -> int:
        """Número de cuentas registradas."""
        return self.usuarios.cantidad()

    def listar(self) -> tuple[UsuarioApp, ...]:
        """Lista cuentas sin devolver hashes ni secretos."""
        return self.usuarios.listar()

    def obtener(self, usuario_id: int) -> UsuarioApp | None:
        return self.usuarios.obtener(usuario_id)

    def crear_administrador_inicial(
        self, *, username: str, nombre: str, password: str
    ) -> UsuarioApp:
        """Crea el primer administrador una única vez."""
        username = self._validar_username(username)
        nombre = self._validar_nombre(nombre)
        password_hash = hash_password(password)
        ahora = self._ahora()

        with self._transaccion():
            if self.usuarios.cantidad() != 0:
                raise ValueError(
                    "La configuración inicial ya se completó. "
                    "Iniciá sesión con una cuenta existente."
                )
            usuario_id = self.usuarios.crear(
                username=username,
                nombre=nombre,
                rol="ADMIN",
                password_hash=password_hash,
                ahora=ahora,
            )
            self._auditar(
                actor=username,
                operacion="USUARIO_ADMIN_INICIAL_CREADO",
                usuario_id=usuario_id,
                datos_nuevos={
                    "username": username,
                    "nombre": nombre,
                    "rol": "ADMIN",
                    "activo": True,
                },
            )
        usuario = self.usuarios.obtener(usuario_id)
        if usuario is None:
            raise RuntimeError("No se pudo leer el administrador recién creado.")
        return usuario

    def autenticar(self, *, username: str, password: str) -> UsuarioApp | None:
        """Autentica de forma genérica; nunca revela si falla usuario o clave."""
        try:
            username_normalizado = self._validar_username(username)
        except ValueError:
            return None

        credencial = self.usuarios.por_username(username_normalizado)
        if credencial is None:
            return None
        usuario, password_hash = credencial
        ahora_dt = datetime.now(timezone.utc)
        if not usuario.activo:
            return None

        hasta = self._parsear_fecha(usuario.bloqueado_hasta)
        if hasta is not None and hasta > ahora_dt:
            return None

        if (
            hasta is not None
            and hasta <= ahora_dt
            and usuario.intentos_login_fallidos >= MAX_INTENTOS_LOGIN
        ):
            with self._transaccion():
                self.usuarios.registrar_fallo_login(
                    usuario.id,
                    intentos=0,
                    bloqueado_hasta=None,
                    ahora=ahora_dt.isoformat(timespec="seconds"),
                )

        if not verificar_password(password, password_hash):
            with self._transaccion():
                actual = self.usuarios.obtener(usuario.id)
                if actual is None or not actual.activo:
                    return None
                bloqueado_actual = self._parsear_fecha(actual.bloqueado_hasta)
                if bloqueado_actual is not None and bloqueado_actual > ahora_dt:
                    return None
                intentos = actual.intentos_login_fallidos + 1
                bloqueo = (
                    (ahora_dt + DURACION_BLOQUEO).isoformat(timespec="seconds")
                    if intentos >= MAX_INTENTOS_LOGIN
                    else None
                )
                self.usuarios.registrar_fallo_login(
                    actual.id,
                    intentos=intentos,
                    bloqueado_hasta=bloqueo,
                    ahora=ahora_dt.isoformat(timespec="seconds"),
                )
            return None

        ahora = ahora_dt.isoformat(timespec="seconds")
        with self._transaccion():
            actual = self.usuarios.obtener(usuario.id)
            if actual is None or not actual.activo:
                return None
            bloqueo = self._parsear_fecha(actual.bloqueado_hasta)
            if bloqueo is not None and bloqueo > ahora_dt:
                return None
            self.usuarios.registrar_login_correcto(actual.id, ahora)
            self._auditar(
                actor=actual.username,
                operacion="INICIO_SESION_LOCAL",
                usuario_id=actual.id,
                datos_nuevos={"username": actual.username},
            )
        return self.usuarios.obtener(usuario.id)

    def crear_usuario(
        self,
        *,
        actor_id: int,
        username: str,
        nombre: str,
        rol: str,
        password: str,
        persona_id: int | None = None,
    ) -> UsuarioApp:
        """Crea una cuenta; el vínculo personal es opcional y no asigna permisos."""
        username = self._validar_username(username)
        nombre = self._validar_nombre(nombre)
        rol = self._validar_rol(rol)
        persona_id = self._validar_persona_vinculada(persona_id)
        password_hash = hash_password(password)
        ahora = self._ahora()

        with self._transaccion():
            actor = self._exigir_administrador(actor_id)
            try:
                usuario_id = self.usuarios.crear(
                    username=username,
                    nombre=nombre,
                    rol=rol,
                    password_hash=password_hash,
                    ahora=ahora,
                    persona_id=persona_id,
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    "Ya existe una cuenta con ese nombre de usuario."
                ) from exc
            self._auditar(
                actor=actor.username,
                operacion="USUARIO_APP_CREADO",
                usuario_id=usuario_id,
                datos_nuevos={
                    "username": username,
                    "nombre": nombre,
                    "rol": rol,
                    "activo": True,
                    "persona_id": persona_id,
                },
            )
        creado = self.usuarios.obtener(usuario_id)
        if creado is None:
            raise RuntimeError("No se pudo leer la cuenta recién creada.")
        return creado

    def actualizar_usuario(
        self,
        *,
        actor_id: int,
        usuario_id: int,
        nombre: str,
        rol: str,
        activo: bool,
        persona_id: int | None | object = _SIN_CAMBIO_PERSONA,
    ) -> UsuarioApp:
        """Actualiza la cuenta, preservando el vínculo si no se indicó otro."""
        nombre = self._validar_nombre(nombre)
        rol = self._validar_rol(rol)
        if not isinstance(activo, bool):
            raise ValueError("El estado de la cuenta no es válido.")
        ahora = self._ahora()

        with self._transaccion():
            actor = self._exigir_administrador(actor_id)
            anterior = self.usuarios.obtener(usuario_id)
            if anterior is None:
                raise ValueError("La cuenta que querés modificar ya no existe.")
            persona_id_nueva = (
                anterior.persona_id
                if persona_id is _SIN_CAMBIO_PERSONA
                else self._validar_persona_vinculada(persona_id)
            )
            if actor_id == usuario_id and not activo:
                raise ValueError(
                    "No podés desactivar tu propia cuenta desde esta sesión."
                )
            quita_ultimo_admin = (
                anterior.activo
                and anterior.rol == "ADMIN"
                and (not activo or rol != "ADMIN")
                and self.usuarios.administradores_activos() <= 1
            )
            if quita_ultimo_admin:
                raise ValueError(
                    "Debe quedar al menos un administrador activo."
                )

            self.usuarios.actualizar_perfil(
                usuario_id,
                nombre=nombre,
                rol=rol,
                activo=activo,
                persona_id=persona_id_nueva,
                ahora=ahora,
            )
            self._auditar(
                actor=actor.username,
                operacion="USUARIO_APP_ACTUALIZADO",
                usuario_id=usuario_id,
                datos_anteriores={
                    "username": anterior.username,
                    "nombre": anterior.nombre,
                    "rol": anterior.rol,
                    "activo": anterior.activo,
                    "persona_id": anterior.persona_id,
                },
                datos_nuevos={
                    "username": anterior.username,
                    "nombre": nombre,
                    "rol": rol,
                    "activo": activo,
                    "persona_id": persona_id_nueva,
                },
            )
        actualizado = self.usuarios.obtener(usuario_id)
        if actualizado is None:
            raise RuntimeError("No se pudo leer la cuenta actualizada.")
        return actualizado

    def restablecer_password(
        self, *, actor_id: int, usuario_id: int, password_nueva: str
    ) -> None:
        """Restablece localmente la contraseña de una cuenta desde el panel admin."""
        password_hash = hash_password(password_nueva)
        ahora = self._ahora()
        with self._transaccion():
            actor = self._exigir_administrador(actor_id)
            objetivo = self.usuarios.obtener(usuario_id)
            if objetivo is None:
                raise ValueError("La cuenta que querés modificar ya no existe.")
            self.usuarios.cambiar_password(usuario_id, password_hash, ahora)
            self._auditar(
                actor=actor.username,
                operacion="PASSWORD_LOCAL_REESTABLECIDA_POR_ADMIN",
                usuario_id=usuario_id,
                datos_nuevos={"username": objetivo.username},
            )

    def restablecer_password_por_acceso_local(
        self, *, username: str, password_nueva: str
    ) -> None:
        """Recuperación offline para el propietario del equipo, no para la UI."""
        username = self._validar_username(username)
        password_hash = hash_password(password_nueva)
        ahora = self._ahora()
        with self._transaccion():
            credencial = self.usuarios.por_username(username)
            if credencial is None:
                raise ValueError("No existe esa cuenta local.")
            objetivo, _ = credencial
            if not objetivo.activo or objetivo.rol != "ADMIN":
                raise ValueError(
                    "La recuperación local solo está habilitada para "
                    "una cuenta ADMIN activa."
                )
            self.usuarios.cambiar_password(objetivo.id, password_hash, ahora)
            self._auditar(
                actor="mantenimiento-local",
                operacion="PASSWORD_ADMIN_REESTABLECIDA_LOCALMENTE",
                usuario_id=objetivo.id,
                datos_nuevos={"username": objetivo.username},
                motivo="Acceso al equipo y a la base local",
            )

    def _exigir_administrador(self, actor_id: int) -> UsuarioApp:
        actor = self.usuarios.obtener(actor_id)
        if actor is None or not actor.activo or actor.rol != "ADMIN":
            raise PermissionError("Se requiere una cuenta ADMIN activa.")
        return actor

    def _validar_persona_vinculada(self, persona_id: int | None) -> int | None:
        """Valida el vínculo opcional sin asignar capacidades por asociación."""
        if persona_id is None:
            return None
        if type(persona_id) is not int or persona_id <= 0:
            raise ValueError("La persona vinculada debe ser una persona existente.")
        persona = self.personas.obtener(persona_id)
        if persona is None:
            raise ValueError("La persona que querés vincular no existe.")
        return persona_id

    @staticmethod
    def _validar_username(username: str) -> str:
        if not isinstance(username, str):
            raise ValueError("El nombre de usuario debe ser texto.")
        normalizado = username.strip().lower()
        if not _USERNAME_RE.fullmatch(normalizado):
            raise ValueError(
                "El usuario debe tener entre 3 y 50 caracteres: letras, "
                "números, punto, guion o guion bajo."
            )
        return normalizado

    @staticmethod
    def _validar_nombre(nombre: str) -> str:
        if not isinstance(nombre, str):
            raise ValueError("El nombre visible debe ser texto.")
        normalizado = nombre.strip()
        if not normalizado or len(normalizado) > 100:
            raise ValueError(
                "El nombre visible es obligatorio y no puede superar 100 caracteres."
            )
        return normalizado

    @staticmethod
    def _validar_rol(rol: str) -> str:
        normalizado = str(rol).strip().upper()
        if normalizado not in ROLES_USUARIO_VALIDOS:
            raise ValueError(
                "Rol inválido. Opciones: " + ", ".join(ROLES_USUARIO_VALIDOS)
            )
        return normalizado

    def _auditar(
        self,
        *,
        actor: str,
        operacion: str,
        usuario_id: int,
        datos_anteriores: dict | None = None,
        datos_nuevos: dict | None = None,
        motivo: str | None = None,
    ) -> None:
        self.auditoria.registrar(
            usuario=actor,
            operacion=operacion,
            entidad="USUARIO_APP",
            entidad_id=usuario_id,
            correlacion_id="cuentas-locales-" + uuid4().hex,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            motivo=motivo,
        )

    @staticmethod
    def _ahora() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _parsear_fecha(valor: str | None) -> datetime | None:
        if not valor:
            return None
        try:
            fecha = datetime.fromisoformat(valor)
        except ValueError:
            return None
        return fecha.replace(tzinfo=timezone.utc) if fecha.tzinfo is None else fecha
