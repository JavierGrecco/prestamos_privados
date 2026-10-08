"""Consola de auditoría global, de solo lectura."""

from __future__ import annotations

import json

import streamlit as st

from aplicacion.servicios.auditoria import FiltrosAuditoria, ServicioAuditoria
from . import componentes


def _fila(entrada):
    return [
        str(entrada.id),
        entrada.fecha,
        entrada.usuario,
        entrada.operacion,
        entrada.entidad,
        "—" if entrada.entidad_id is None else str(entrada.entidad_id),
        (entrada.motivo or "—"),
        entrada.correlacion_id[:12] + "…",
    ]


def render(db) -> None:
    componentes.render_html('<div class="detalle-titulo">Auditoría</div>')
    componentes.render_html(
        '<div class="saludo">Trazabilidad de cambios y decisiones del sistema</div>'
    )

    servicio = ServicioAuditoria(db)

    operaciones = ["TODAS"] + servicio.operaciones()
    entidades = ["TODAS"] + servicio.entidades()

    col1, col2, col3 = st.columns(3)
    with col1:
        usuario = st.text_input(
            "Usuario",
            placeholder="Ej: admin",
            key="auditoria_usuario",
        ).strip()
    with col2:
        operacion = st.selectbox(
            "Operación",
            options=operaciones,
            format_func=lambda x: "Todas" if x == "TODAS" else x,
            key="auditoria_operacion",
        )
    with col3:
        entidad = st.selectbox(
            "Entidad",
            options=entidades,
            format_func=lambda x: "Todas" if x == "TODAS" else x,
            key="auditoria_entidad",
        )

    filtros = FiltrosAuditoria(
        usuario=usuario or None,
        operacion=None if operacion == "TODAS" else operacion,
        entidad=None if entidad == "TODAS" else entidad,
        limite=200,
    )
    entradas = servicio.listar(filtros)

    st.caption(f"{len(entradas)} eventos visibles")

    if not entradas:
        componentes.estado_vacio(
            icono="🧭",
            titulo="No hay eventos para estos filtros",
            texto="La auditoría no se modifica desde esta pantalla.",
        )
        return

    componentes.tabla(
        [
            {"texto": "ID"},
            {"texto": "Fecha"},
            {"texto": "Usuario"},
            {"texto": "Operación"},
            {"texto": "Entidad"},
            {"texto": "ID entidad"},
            {"texto": "Motivo"},
            {"texto": "Correlación"},
        ],
        [_fila(e) for e in entradas],
    )

    ids = [e.id for e in entradas]
    seleccionado = st.selectbox(
        "Evento para inspeccionar",
        options=ids,
        format_func=lambda x: f"#{x}",
        key="auditoria_evento_seleccionado",
    )
    entrada = next(e for e in entradas if e.id == seleccionado)

    componentes.render_html('<div class="seccion-titulo">Detalle del evento</div>')
    componentes.tabla(
        [
            {"texto": "Campo"},
            {"texto": "Valor"},
        ],
        [
            ["Fecha", entrada.fecha],
            ["Usuario", entrada.usuario],
            ["Operación", entrada.operacion],
            ["Entidad", entrada.entidad],
            ["ID entidad", "—" if entrada.entidad_id is None else str(entrada.entidad_id)],
            ["Motivo", entrada.motivo or "—"],
            ["Correlación", entrada.correlacion_id],
        ],
    )

    with st.expander("Datos anteriores / nuevos"):
        col1, col2 = st.columns(2)
        with col1:
            st.json(
                json.loads(entrada.datos_anteriores)
                if entrada.datos_anteriores
                else {}
            )
        with col2:
            st.json(
                json.loads(entrada.datos_nuevos)
                if entrada.datos_nuevos
                else {}
            )

    correlacion = servicio.por_correlacion(entrada.correlacion_id)
    componentes.render_html('<div class="seccion-titulo">Operación completa</div>')
    if len(correlacion) == 1:
        componentes.render_html(
            '<div class="caption-ayuda">No hay otros eventos con esta correlación.</div>'
        )
    else:
        componentes.tabla(
            [
                {"texto": "ID"},
                {"texto": "Fecha"},
                {"texto": "Usuario"},
                {"texto": "Operación"},
                {"texto": "Entidad"},
                {"texto": "Motivo"},
            ],
            [
                [
                    str(e.id),
                    e.fecha,
                    e.usuario,
                    e.operacion,
                    e.entidad,
                    e.motivo or "—",
                ]
                for e in correlacion
            ],
        )
