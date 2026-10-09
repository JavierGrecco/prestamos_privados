"""Catálogo único de páginas, grupos y capacidades de navegación.

La navegación presenta solo las superficies que la cuenta puede abrir. La
autorización se vuelve a comprobar en el punto de entrada de cada pantalla;
el menú nunca es la única barrera de seguridad.
"""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from aplicacion.seguridad.capacidades import (
    CAP_ADMINISTRAR_SISTEMA,
    CAP_ADMINISTRAR_USUARIOS,
    CAP_OPERAR,
    CAP_VER_AUDITORIA,
    CAP_VER_MOTOR_V3,
    CAP_VER_PERSONA,
    PoliticaCapacidades,
)
from aplicacion.seguridad.identidad import IdentidadSesion


@dataclass(frozen=True)
class DefinicionPagina:
    """Contrato visible de una superficie de la aplicación."""

    clave: str
    etiqueta: str
    grupo: str
    capacidad: str
    requiere_persona: bool = False
    navegable: bool = True
    pagina_padre: str | None = None
    nivel: str = "habitual"


GRUPOS_NAVEGACION = (
    "Inicio",
    "Cartera",
    "Análisis e informes",
    "Administración",
)

CATALOGO_PAGINAS: tuple[DefinicionPagina, ...] = (
    DefinicionPagina(
        "resumen", "Resumen", "Inicio", CAP_VER_PERSONA,
        requiere_persona=True,
    ),
    DefinicionPagina(
        "mi_espacio", "Mi espacio", "Inicio", CAP_VER_PERSONA,
    ),
    DefinicionPagina(
        "personas", "Personas", "Cartera", CAP_OPERAR,
    ),
    DefinicionPagina(
        "prestamos", "Préstamos", "Cartera", CAP_OPERAR,
        requiere_persona=True,
    ),
    DefinicionPagina(
        "pagos", "Pagos", "Cartera", CAP_OPERAR,
        requiere_persona=True,
    ),
    DefinicionPagina(
        "analisis", "Análisis financiero", "Análisis e informes",
        CAP_VER_PERSONA, requiere_persona=True,
    ),
    DefinicionPagina(
        "planificar", "Planificación", "Análisis e informes",
        CAP_VER_PERSONA, requiere_persona=True,
    ),
    DefinicionPagina(
        "escenarios", "Escenarios", "Análisis e informes",
        CAP_VER_PERSONA, requiere_persona=True,
    ),
    DefinicionPagina(
        "rendimiento", "Rendimiento", "Análisis e informes",
        CAP_VER_PERSONA, requiere_persona=True,
    ),
    DefinicionPagina(
        "comparar", "Comparar", "Análisis e informes",
        CAP_VER_PERSONA, requiere_persona=True,
    ),
    DefinicionPagina(
        "reportes", "Reportes", "Análisis e informes",
        CAP_VER_PERSONA, requiere_persona=True,
    ),
    DefinicionPagina(
        "auditoria", "Auditoría", "Administración", CAP_VER_AUDITORIA,
    ),
    DefinicionPagina(
        "usuarios", "Usuarios y accesos", "Administración",
        CAP_ADMINISTRAR_USUARIOS, nivel="administracion",
    ),
    DefinicionPagina(
        "operacion", "Operación del sistema", "Administración",
        CAP_ADMINISTRAR_SISTEMA, nivel="avanzado",
    ),
    DefinicionPagina(
        "motor_v3", "Motor de pagos avanzado", "Administración",
        CAP_VER_MOTOR_V3, nivel="avanzado",
    ),
    DefinicionPagina(
        "detalle_financiero", "Detalle financiero", "Cartera",
        CAP_OPERAR, requiere_persona=True, navegable=False,
        pagina_padre="prestamos", nivel="contextual",
    ),
)

PAGINAS_POR_CLAVE: dict[str, DefinicionPagina] = {
    pagina.clave: pagina for pagina in CATALOGO_PAGINAS
}

# Compatibilidad para módulos que solo necesitan el catálogo de opciones
# navegables. Las páginas contextuales no se agregan al menú raíz.
PAGINAS: dict[str, str] = {
    pagina.clave: pagina.etiqueta
    for pagina in CATALOGO_PAGINAS
    if pagina.navegable
}


def paginas_permitidas_para(
    identidad: IdentidadSesion,
    politica: PoliticaCapacidades | None = None,
) -> tuple[str, ...]:
    """Devuelve las páginas navegables permitidas para una identidad."""
    resolvedor = politica or PoliticaCapacidades()
    return tuple(
        pagina.clave
        for pagina in CATALOGO_PAGINAS
        if pagina.navegable and resolvedor.puede(identidad, pagina.capacidad)
    )


def capacidad_requerida_para_pagina(clave: str) -> str | None:
    """Capacidad que protege la ruta, incluso si no figura en el menú raíz."""
    pagina = PAGINAS_POR_CLAVE.get(clave)
    return pagina.capacidad if pagina is not None else None


def requiere_persona_para_pagina(clave: str) -> bool:
    """Indica si la página necesita la persona financiera seleccionada."""
    pagina = PAGINAS_POR_CLAVE.get(clave)
    return pagina.requiere_persona if pagina is not None else False


def renderizar_navegacion(
    paginas_permitidas: tuple[str, ...] | None = None,
) -> str:
    """Renderiza una navegación lateral agrupada y devuelve la ruta activa."""
    permitidas = (
        tuple(PAGINAS)
        if paginas_permitidas is None
        else tuple(clave for clave in paginas_permitidas if clave in PAGINAS)
    )
    if not permitidas:
        st.sidebar.info("Esta cuenta todavía no tiene páginas disponibles.")
        return st.session_state.get("pagina", "")

    actual = st.session_state.get("pagina", "resumen")
    definicion_actual = PAGINAS_POR_CLAVE.get(actual)
    if definicion_actual is None or (
        definicion_actual.navegable and actual not in permitidas
    ):
        actual = permitidas[0]
        st.session_state["pagina"] = actual

    st.sidebar.markdown("**Mis Préstamos**")
    st.sidebar.markdown("Gestión financiera")
    for grupo in GRUPOS_NAVEGACION:
        del_grupo = [
            PAGINAS_POR_CLAVE[clave]
            for clave in permitidas
            if PAGINAS_POR_CLAVE[clave].grupo == grupo
        ]
        if not del_grupo:
            continue

        st.sidebar.markdown(f"**{grupo.upper()}**")
        for definicion in del_grupo:
            pagina_contextual = PAGINAS_POR_CLAVE.get(actual)
            es_activa = definicion.clave == actual or (
                pagina_contextual is not None
                and not pagina_contextual.navegable
                and pagina_contextual.pagina_padre == definicion.clave
            )
            prefijo = "●" if es_activa else "○"
            envoltorio = "nav-activo" if es_activa else "nav-opcion"
            with st.sidebar.container(key=f"{envoltorio}-{definicion.clave}"):
                if st.button(
                    f"{prefijo}  {definicion.etiqueta}",
                    key=f"nav_{definicion.clave}",
                    use_container_width=True,
                ):
                    st.session_state["pagina"] = definicion.clave
                    st.rerun()

    return st.session_state.get("pagina", actual)
