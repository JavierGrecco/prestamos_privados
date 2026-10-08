"""Pantalla de estado y control del Motor de Pagos V3."""

from __future__ import annotations

from decimal import Decimal

import streamlit as st

from aplicacion.servicios.metricas_sombra_v3 import ServicioMetricasSombraV3
from aplicacion.servicios.puente_motor_pago_v3 import ModoMotorPagoV3
from aplicacion.servicios.registro_pago_ui import ServicioRegistroPagoUI
from . import componentes


ETIQUETAS_MODO = {
    "LEGACY": "Legacy",
    "SOMBRA": "Sombra",
    "V3": "V3 efectivo",
}


def renderizar_selector_modo(servicio: ServicioRegistroPagoUI) -> ModoMotorPagoV3:
    actual = st.session_state.get(
        "motor_pago_modo_solicitado",
        ModoMotorPagoV3.SOMBRA.value,
    )
    opciones = [modo.value for modo in ModoMotorPagoV3]

    componentes.render_html('<div class="etiqueta-control">Motor de pagos</div>')
    seleccionado = st.segmented_control(
        "Motor de pagos",
        options=opciones,
        format_func=lambda x: ETIQUETAS_MODO[x],
        default=actual,
        label_visibility="collapsed",
        key="motor_pago_modo_solicitado",
    )

    modo = ModoMotorPagoV3(seleccionado or actual)

    if modo is ModoMotorPagoV3.V3:
        preflight = servicio.evaluar_preflight()
        if preflight.apto:
            componentes.render_html(
                '<div class="nota-contextual nota-success">'
                '<span class="nota-icono">✓</span>'
                '<span class="nota-texto">V3 está habilitado por preflight aprobado.</span>'
                '</div>'
            )
        else:
            componentes.render_html(
                '<div class="nota-contextual nota-warning">'
                '<span class="nota-icono">⚠</span>'
                '<span class="nota-texto">'
                'V3 efectivo todavía no está habilitado. Revisá los criterios '
                'del preflight más abajo.'
                '</span></div>'
            )
    elif modo is ModoMotorPagoV3.SOMBRA:
        componentes.render_html(
            '<div class="nota-contextual nota-info">'
            '<span class="nota-icono">◌</span>'
            '<span class="nota-texto">'
            'Sombra: Legacy registra el pago y V3 calcula sobre el snapshot '
            'previo para comparar y medir.'
            '</span></div>'
        )
    else:
        componentes.render_html(
            '<div class="nota-contextual nota-info">'
            '<span class="nota-icono">○</span>'
            '<span class="nota-texto">Legacy es el flujo histórico efectivo.</span>'
            '</div>'
        )

    return modo


def render(db, prestamo_id: int | None = None) -> None:
    componentes.render_html('<div class="detalle-titulo">Motor de Pagos V3</div>')
    componentes.render_html(
        '<div class="saludo">Estado, evidencia y condición de activación</div>'
    )

    servicio = ServicioRegistroPagoUI(db)
    modo = renderizar_selector_modo(servicio)
    preflight = servicio.evaluar_preflight()

    metricas = ServicioMetricasSombraV3(db).obtener(prestamo_id)

    componentes.render_html('<div class="seccion-titulo">Evidencia SOMBRA</div>')
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Ejecuciones", metricas.ejecuciones_sombra)
    with col2:
        tasa = metricas.tasa_coincidencia
        texto = "—" if tasa is None else f"{Decimal(str(tasa)) * 100:.2f}%"
        st.metric("Coincidencia", texto)
    with col3:
        st.metric("Divergencias", metricas.ejecuciones_con_divergencia)
    with col4:
        st.metric("Errores", metricas.ejecuciones_con_error)

    if not metricas.hay_observaciones:
        componentes.render_html(
            '<div class="nota-contextual nota-info">'
            '<span class="nota-icono">◌</span>'
            '<span class="nota-texto">'
            'Todavía no hay observaciones SOMBRA persistidas. La pantalla de '
            'registro empezará a generarlas cuando uses el modo Sombra.'
            '</span></div>'
        )

    componentes.render_html('<div class="seccion-titulo">Preflight V3</div>')
    filas = []
    for criterio in preflight.criterios:
        estado = "✓ Cumple" if criterio.cumplido else "✗ No cumple"
        filas.append([criterio.nombre, estado, criterio.detalle])

    componentes.tabla(
        [
            {"texto": "Criterio"},
            {"texto": "Estado"},
            {"texto": "Detalle"},
        ],
        filas,
    )

    if preflight.apto:
        componentes.render_html(
            '<div class="nota-contextual nota-success">'
            '<span class="nota-icono">✓</span>'
            '<span class="nota-texto">'
            'Todos los criterios del preflight están aprobados. V3 puede ser '
            'seleccionado como modo efectivo por la frontera de aplicación.'
            '</span></div>'
        )
    else:
        componentes.render_html(
            '<div class="nota-contextual nota-warning">'
            '<span class="nota-icono">⚠</span>'
            '<span class="nota-texto">'
            'V3 efectivo permanece bloqueado hasta cumplir todos los criterios.'
            '</span></div>'
        )

    if modo is ModoMotorPagoV3.SOMBRA and metricas.ejecuciones_sombra > 0:
        componentes.render_html('<div class="seccion-titulo">Última evidencia</div>')
        componentes.render_html(
            f'<div class="detalle-item">'
            f'<span>Primera ejecución</span>'
            f'<strong>{metricas.primera_observacion or "—"}</strong>'
            f'</div>'
            f'<div class="detalle-item">'
            f'<span>Última ejecución</span>'
            f'<strong>{metricas.ultima_observacion or "—"}</strong>'
            f'</div>'
        )
