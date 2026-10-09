"""Pantallas de acceso y primera configuración de la cuenta local."""

from __future__ import annotations

import streamlit as st

from aplicacion.servicios.usuarios_locales import ServicioUsuariosLocales
from infraestructura.db import BaseDatos
from infraestructura.repositorios.usuarios_app import UsuarioApp
from . import componentes


def sesion_local_vigente(
    usuario: UsuarioApp,
    revision_guardada: object,
) -> bool:
    """Comprueba que la sesión no preceda a un cambio de credenciales/permisos."""
    return (
        type(revision_guardada) is int
        and revision_guardada == usuario.revision_sesion
    )


def obtener_usuario_autenticado(db: BaseDatos) -> UsuarioApp | None:
    """Devuelve la cuenta válida de la sesión o presenta acceso/configuración."""
    servicio = ServicioUsuariosLocales(db)
    usuario_id = st.session_state.get("usuario_app_id")

    if usuario_id is not None:
        usuario = servicio.obtener(usuario_id)
        revision_guardada = st.session_state.get("usuario_app_revision")
        if (
            usuario is not None
            and usuario.activo
            and sesion_local_vigente(usuario, revision_guardada)
        ):
            return usuario

        st.session_state.pop("usuario_app_id", None)
        st.session_state.pop("usuario_app_revision", None)
        if usuario is None or not usuario.activo:
            mensaje = (
                "La sesión terminó porque la cuenta ya no existe o fue desactivada."
            )
        else:
            mensaje = (
                "La sesión se cerró porque cambiaron las credenciales, los "
                "permisos o la persona vinculada a esta cuenta. Iniciá sesión nuevamente."
            )
        st.session_state["mensaje_sesion_expirada"] = mensaje

    st.markdown(
        "<div class='detalle-titulo'>Mis Préstamos</div>",
        unsafe_allow_html=True,
    )
    st.caption("Acceso local a la información financiera.")

    mensaje = st.session_state.pop("mensaje_sesion_expirada", None)
    if mensaje:
        componentes.nota_contextual(mensaje, "warning")
    error = st.session_state.pop("error_acceso_local", None)
    if error:
        componentes.nota_contextual(error, "error")

    if servicio.cantidad() == 0:
        _configurar_administrador(servicio)
    else:
        _iniciar_sesion(servicio)
    return None


def _configurar_administrador(servicio: ServicioUsuariosLocales) -> None:
    st.title("Configurar administrador local")
    st.write(
        "Esta base todavía no tiene cuentas. Creá la primera cuenta "
        "**admin**; será el único paso de configuración inicial. "
        "Elegí una contraseña larga y guardala en un lugar seguro."
    )
    componentes.nota_contextual(
        "Este asistente es para la ejecución local. No expongas el servidor "
        "a Internet: todavía no hay registro público, proveedor de identidad "
        "online ni recuperación de contraseña por email.",
        "warning",
    )
    with st.form("configurar_admin_local"):
        username = st.text_input(
            "Nombre de usuario",
            value="admin",
            help="Podés usar letras, números, punto, guion o guion bajo.",
        )
        nombre = st.text_input("Nombre para mostrar", value="Administrador local")
        password = st.text_input(
            "Crear contraseña",
            type="password",
            help="Usá al menos 12 caracteres.",
        )
        confirmar = st.text_input("Repetir contraseña", type="password")
        enviar = st.form_submit_button(
            "Crear administrador",
            use_container_width=True,
        )

    if not enviar:
        return
    if password != confirmar:
        st.session_state["error_acceso_local"] = "Las contraseñas no coinciden."
        st.rerun()
    try:
        usuario = servicio.crear_administrador_inicial(
            username=username,
            nombre=nombre,
            password=password,
        )
    except Exception as exc:
        st.session_state["error_acceso_local"] = str(exc)
        st.rerun()
    st.session_state["usuario_app_id"] = usuario.id
    st.session_state["usuario_app_revision"] = usuario.revision_sesion
    st.rerun()


def _iniciar_sesion(servicio: ServicioUsuariosLocales) -> None:
    st.title("Iniciar sesión")
    with st.form("iniciar_sesion_local"):
        username = st.text_input("Usuario", key="acceso_usuario")
        password = st.text_input(
            "Contraseña",
            type="password",
            key="acceso_password",
        )
        enviar = st.form_submit_button(
            "Ingresar",
            use_container_width=True,
        )

    if enviar:
        usuario = servicio.autenticar(username=username, password=password)
        if usuario is None:
            st.session_state["error_acceso_local"] = (
                "No se pudo iniciar sesión. Revisá usuario y contraseña, "
                "y verificá que la cuenta esté activa y no bloqueada."
            )
            st.rerun()
        st.session_state["usuario_app_id"] = usuario.id
        st.session_state["usuario_app_revision"] = usuario.revision_sesion
        st.rerun()

    st.caption(
        "¿Olvidaste la contraseña? En esta versión la recuperación es local, "
        "con acceso al equipo y a la base. La recuperación por email se "
        "incorporará cuando exista autenticación online."
    )
    st.markdown(
        "[Guía de recuperación y administración local](OPERACION_USUARIOS_LOCALES.md)"
    )
