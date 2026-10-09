"""Administración de cuentas de acceso para el modo local."""

from __future__ import annotations

import streamlit as st

from aplicacion.servicios.usuarios_locales import (
    ROLES_USUARIO_VALIDOS,
    ServicioUsuariosLocales,
)
from infraestructura.repositorios.usuarios_app import UsuarioApp
from . import componentes


ETIQUETAS_ROL = {
    "ADMIN": "Administrador",
    "OPERADOR": "Operador",
    "LECTURA": "Solo lectura",
}


def _listado(servicio: ServicioUsuariosLocales) -> None:
    usuarios = servicio.listar()
    st.metric("Cuentas registradas", len(usuarios))
    filas = [
        [
            usuario.username,
            usuario.nombre,
            ETIQUETAS_ROL[usuario.rol],
            "Activa" if usuario.activo else "Desactivada",
            usuario.ultimo_acceso_en or "Todavía no inició sesión",
        ]
        for usuario in usuarios
    ]
    componentes.tabla(
        [
            {"texto": "Usuario"},
            {"texto": "Nombre"},
            {"texto": "Rol"},
            {"texto": "Estado"},
            {"texto": "Último acceso"},
        ],
        filas,
    )


def _crear(servicio: ServicioUsuariosLocales, actor: UsuarioApp) -> None:
    st.markdown("### Crear una cuenta")
    st.caption(
        "La cuenta sirve para iniciar sesión en esta aplicación. "
        "No es lo mismo que una persona de un préstamo."
    )
    with st.form("usuarios_admin_crear"):
        username = st.text_input(
            "Nombre de usuario *",
            placeholder="ej. operador_maria",
            help="Entre 3 y 50 caracteres: letras, números, punto, guion o guion bajo.",
        )
        nombre = st.text_input("Nombre para mostrar *")
        rol = st.selectbox(
            "Rol inicial",
            options=list(ROLES_USUARIO_VALIDOS),
            format_func=lambda x: ETIQUETAS_ROL[x],
            index=1,
        )
        password = st.text_input(
            "Contraseña inicial *",
            type="password",
            help="Al menos 12 caracteres. Entregala por un canal privado.",
        )
        confirmar = st.text_input("Repetir contraseña *", type="password")
        enviar = st.form_submit_button("Crear usuario", use_container_width=True)

    if not enviar:
        return
    if password != confirmar:
        componentes.nota_contextual("Las contraseñas no coinciden.", "error")
        return
    try:
        usuario = servicio.crear_usuario(
            actor_id=actor.id,
            username=username,
            nombre=nombre,
            rol=rol,
            password=password,
        )
    except Exception as exc:
        componentes.nota_contextual(str(exc), "error")
        return
    componentes.disparar_nota(
        f"La cuenta @{usuario.username} fue creada.",
        "success",
    )
    st.rerun()


def _administrar(servicio: ServicioUsuariosLocales, actor: UsuarioApp) -> None:
    usuarios = servicio.listar()
    if not usuarios:
        componentes.estado_vacio(
            "👤",
            "No hay cuentas",
            "Creá la primera cuenta desde la pestaña Crear usuario.",
        )
        return

    opciones = {usuario.id: usuario for usuario in usuarios}
    actual = st.session_state.get("usuarios_admin_seleccion")
    if actual not in opciones:
        actual = actor.id if actor.id in opciones else usuarios[0].id

    usuario_id = st.selectbox(
        "Cuenta que querés administrar",
        options=list(opciones),
        index=list(opciones).index(actual),
        format_func=lambda x: (
            f"{opciones[x].username} — {opciones[x].nombre}"
            + ("" if opciones[x].activo else " (desactivada)")
        ),
        key="usuarios_admin_seleccion",
    )
    objetivo = servicio.obtener(usuario_id)
    if objetivo is None:
        componentes.nota_contextual(
            "La cuenta dejó de existir. Actualizá el listado.",
            "warning",
        )
        return

    with st.form(f"usuarios_admin_perfil_{usuario_id}"):
        nombre = st.text_input("Nombre para mostrar", value=objetivo.nombre)
        rol = st.selectbox(
            "Rol",
            options=list(ROLES_USUARIO_VALIDOS),
            index=list(ROLES_USUARIO_VALIDOS).index(objetivo.rol),
            format_func=lambda x: ETIQUETAS_ROL[x],
        )
        activo = st.checkbox(
            "Cuenta activa: puede iniciar sesión",
            value=objetivo.activo,
            disabled=objetivo.id == actor.id,
        )
        guardar = st.form_submit_button(
            "Guardar cambios de acceso",
            use_container_width=True,
        )

    if guardar:
        try:
            servicio.actualizar_usuario(
                actor_id=actor.id,
                usuario_id=objetivo.id,
                nombre=nombre,
                rol=rol,
                activo=activo if objetivo.id != actor.id else objetivo.activo,
            )
        except Exception as exc:
            componentes.nota_contextual(str(exc), "error")
        else:
            componentes.disparar_nota("Cuenta actualizada.", "success")
            st.rerun()

    st.markdown("### Restablecer contraseña")
    st.caption(
        "El cambio se aplica inmediatamente. La aplicación nunca muestra "
        "ni conserva la contraseña anterior."
    )
    with st.form(f"usuarios_admin_password_{usuario_id}"):
        password_nueva = st.text_input(
            "Nueva contraseña",
            type="password",
            key=f"usuarios_admin_password_nueva_{usuario_id}",
        )
        password_confirmacion = st.text_input(
            "Repetir nueva contraseña",
            type="password",
            key=f"usuarios_admin_password_confirmacion_{usuario_id}",
        )
        reset = st.form_submit_button(
            "Restablecer contraseña",
            use_container_width=True,
        )
    if reset:
        if password_nueva != password_confirmacion:
            componentes.nota_contextual(
                "Las contraseñas no coinciden.",
                "error",
            )
            return
        try:
            servicio.restablecer_password(
                actor_id=actor.id,
                usuario_id=objetivo.id,
                password_nueva=password_nueva,
            )
        except Exception as exc:
            componentes.nota_contextual(str(exc), "error")
        else:
            componentes.disparar_nota(
                f"Se cambió la contraseña de @{objetivo.username}.",
                "success",
            )
            st.rerun()


def render(db, usuario_actual: UsuarioApp) -> None:
    """Renderiza la consola de administración de cuentas."""
    componentes.renderizar_nota_pendiente()
    st.title("Administrar usuarios")
    st.caption(
        "Gestioná quién puede ingresar y qué puede hacer en la aplicación local."
    )
    componentes.nota_contextual(
        "Los roles asignan capacidades dentro de la aplicación. "
        "La cuenta ADMIN puede administrar otras cuentas; OPERADOR puede operar; "
        "LECTURA permite consultar sin registrar operaciones. "
        "Las personas y sus roles de préstamo se administran en Personas.",
        "info",
    )

    servicio = ServicioUsuariosLocales(db)
    pestañas = st.tabs(["Cuentas", "Crear usuario", "Administrar cuenta"])
    with pestañas[0]:
        _listado(servicio)
    with pestañas[1]:
        _crear(servicio, usuario_actual)
    with pestañas[2]:
        _administrar(servicio, usuario_actual)
