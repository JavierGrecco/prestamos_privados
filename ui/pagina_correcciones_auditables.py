"""Historial de propuestas de corrección auditable, de solo lectura."""

from __future__ import annotations

import json

import streamlit as st

from aplicacion.seguridad.identidad import IdentidadSesion
from infraestructura.composicion.correcciones_auditables import (
    crear_servicio_correcciones_auditables,
)
from dominio.excepciones import ErrorValidacion
from . import componentes


def _etiqueta_propuesta(propuesta) -> str:
    """Etiqueta de selector legible y no ambigua."""
    return (
        f"#{propuesta.id} · {propuesta.entidad_tipo} "
        f"· registro #{propuesta.entidad_id} · {propuesta.corregido_en_utc}"
    )


def render(db, identidad: IdentidadSesion) -> None:
    """Muestra propuestas auditables sin cambiar datos financieros efectivos."""
    componentes.render_html(
        '<div class="detalle-titulo">Correcciones auditables</div>'
    )
    componentes.render_html(
        '<div class="saludo">Historial y comparación de propuestas financieras</div>'
    )
    st.caption(
        "Esta pantalla muestra propuestas registradas. Ninguna propuesta se aplica "
        "automáticamente a aportes, flujos, valuaciones, rendimientos ni reportes."
    )

    try:
        servicio = crear_servicio_correcciones_auditables(db, identidad=identidad)
        propuestas = servicio.listar_recientes(limite=200)
    except PermissionError as exc:
        componentes.nota_contextual(str(exc), "error")
        return
    except ErrorValidacion as exc:
        componentes.nota_contextual(
            "No se puede mostrar el historial porque una verificación de integridad "
            f"no pasó: {exc}",
            "error",
        )
        return

    if not propuestas:
        componentes.estado_vacio(
            icono="🧾",
            titulo="Todavía no hay propuestas de corrección",
            texto=(
                "Cuando se registre una propuesta desde un flujo autorizado, "
                "aparecerá aquí para su inspección. Esta pantalla es de consulta; "
                "no crea ni aplica correcciones."
            ),
        )
        return

    st.caption(f"{len(propuestas)} propuestas recientes verificadas")
    opciones = [propuesta.id for propuesta in propuestas]
    seleccionada_id = st.selectbox(
        "Propuesta para inspeccionar",
        options=opciones,
        format_func=lambda propuesta_id: _etiqueta_propuesta(
            next(p for p in propuestas if p.id == propuesta_id)
        ),
        key="correcciones_auditables_seleccionada",
    )
    propuesta = next(p for p in propuestas if p.id == seleccionada_id)

    st.info(
        "La corrección seleccionada es una propuesta auditable, no un cambio aplicado. "
        "El registro financiero original se conserva."
    )
    componentes.tabla(
        [{"texto": "Dato"}, {"texto": "Valor"}],
        [
            ["Propuesta", f"#{propuesta.id}"],
            ["Tipo de registro", propuesta.entidad_tipo],
            ["ID del registro original", str(propuesta.entidad_id)],
            ["Responsable autenticado", propuesta.corregido_por],
            ["Fecha UTC", propuesta.corregido_en_utc],
            ["Motivo", propuesta.motivo],
            [
                "Propuesta anterior",
                "—" if propuesta.correccion_anterior_id is None
                else f"#{propuesta.correccion_anterior_id}",
            ],
            ["Estado", "Registrada · no aplicada"],
        ],
    )

    try:
        snapshot_original = servicio.obtener_snapshot_original(propuesta)
    except ErrorValidacion as exc:
        componentes.nota_contextual(
            "El historial de la propuesta pasó su verificación, pero no se puede "
            "mostrar una comparación confiable con el registro original actual. "
            f"Detalle: {exc}",
            "error",
        )
        snapshot_original = None

    with st.expander("Comparación de datos", expanded=True):
        if snapshot_original is None:
            st.caption(
                "No se muestra el lado original porque su integridad o correspondencia "
                "con la propuesta no pudo verificarse."
            )
        else:
            original_col, corregido_col = st.columns(2)
            with original_col:
                st.markdown("**Snapshot original verificado**")
                st.json(snapshot_original, expanded=False)
            with corregido_col:
                st.markdown("**Snapshot propuesto**")
                st.json(
                    json.loads(propuesta.snapshot_corregido_json),
                    expanded=False,
                )

    with st.expander("Huellas de integridad y trazabilidad"):
        st.write("**SHA-256 original**")
        st.code(propuesta.hash_original, language=None)
        st.write("**SHA-256 de la propuesta**")
        st.code(propuesta.hash_corregido, language=None)
        st.caption(
            "Los hashes permiten detectar modificaciones del contenido. "
            "La propuesta no reemplaza al registro original."
        )
