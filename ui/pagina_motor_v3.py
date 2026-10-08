"""Pantalla de estado y control del Motor de Pagos V3."""

from __future__ import annotations

from decimal import Decimal

import streamlit as st

from aplicacion.servicios import ErrorDatosInvalidos, ErrorEstadoInvalido
from aplicacion.servicios.metricas_sombra_v3 import ServicioMetricasSombraV3
from aplicacion.servicios.precheck_canary_motor_pago_v3 import ServicioReadinessCanaryV3
from aplicacion.servicios.puente_motor_pago_v3 import ModoMotorPagoV3
from aplicacion.servicios.registro_pago_ui import ServicioRegistroPagoUI
from ui.contexto_operador import operador_actual
from . import componentes


ETIQUETAS_MODO = {
    "LEGACY": "Legacy",
    "SOMBRA": "Sombra",
    "V3": "V3 efectivo",
}


def renderizar_selector_modo(servicio: ServicioRegistroPagoUI) -> ModoMotorPagoV3:
    estado = servicio.modo_actual()

    if "motor_pago_modo_solicitado" not in st.session_state:
        st.session_state["motor_pago_modo_solicitado"] = estado.value

    seleccionado = st.segmented_control(
        "Motor de pagos",
        options=[modo.value for modo in ModoMotorPagoV3],
        format_func=lambda x: ETIQUETAS_MODO[x],
        label_visibility="collapsed",
        key="motor_pago_modo_solicitado",
    )
    seleccionado = seleccionado or estado.value
    modo_seleccionado = ModoMotorPagoV3(seleccionado)

    if modo_seleccionado is not estado:
        componentes.render_html(
            '<div class="nota-contextual nota-warning">'
            '<span class="nota-icono">⚠</span>'
            '<span class="nota-texto">'
            f'Modo efectivo actual: <strong>{ETIQUETAS_MODO[estado.value]}</strong>. '
            'El cambio todavía no está aplicado.'
            '</span></div>'
        )
        motivo = st.text_input(
            "Motivo del cambio",
            placeholder="Ej: inicio del canary V3",
            key="motor_pago_motivo_cambio",
        )
        if st.button(
            f"Aplicar {ETIQUETAS_MODO[modo_seleccionado.value]}",
            use_container_width=True,
            key="aplicar_modo_motor_pago",
            disabled=not motivo.strip(),
        ):
            try:
                servicio.cambiar_modo(
                    nuevo_modo=modo_seleccionado,
                    usuario=operador_actual(),
                    motivo=motivo,
                )
            except (ErrorDatosInvalidos, ErrorEstadoInvalido) as exc:
                componentes.disparar_nota(str(exc), "error")
            else:
                st.session_state.pop("motor_pago_motivo_cambio", None)
                componentes.disparar_nota(
                    f"Modo de pagos cambiado a {ETIQUETAS_MODO[modo_seleccionado.value]}.",
                    "success",
                )
                st.rerun()
        return estado

    modo = estado

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

    readiness = ServicioReadinessCanaryV3(db).evaluar()

    componentes.render_html('<div class="seccion-titulo">Readiness de canary</div>')

    if readiness.listo:
        componentes.render_html(
            '<div class="nota-contextual nota-success">'
            '<span class="nota-icono">✓</span>'
            '<span class="nota-texto">'
            'La base está <strong>lista para un canary V3</strong>. '
            f'Modo actual: <strong>{ETIQUETAS_MODO[readiness.modo_actual]}</strong> · '
            f'Revisión {readiness.revision_modo}.'
            '</span></div>'
        )
    else:
        componentes.render_html(
            '<div class="nota-contextual nota-warning">'
            '<span class="nota-icono">⚠</span>'
            '<span class="nota-texto">'
            '<strong>La base todavía no está lista para canary V3.</strong>'
            '</span></div>'
        )

    readiness_rows = [
        ["Integridad V3", "✓ Cumple" if readiness.integridad_ok else "✗ No cumple"],
        ["Preflight", "✓ Cumple" if readiness.preflight_apto else "✗ No cumple"],
        ["Modo previo al canary", "✓ Sí" if readiness.modo_actual in {"LEGACY", "SOMBRA"} else "✗ No"],
        ["Ejecuciones SOMBRA", str(readiness.ejecuciones_sombra)],
        [
            "Coincidencia",
            "—" if readiness.tasa_coincidencia is None
            else f"{Decimal(str(readiness.tasa_coincidencia)) * 100:.2f}%",
        ],
        ["Divergencias", str(readiness.divergencias)],
        ["Errores", str(readiness.errores)],
    ]
    componentes.tabla(
        [
            {"texto": "Control"},
            {"texto": "Resultado"},
        ],
        readiness_rows,
    )

    if readiness.motivos_rechazo:
        componentes.render_html(
            '<div class="caption-ayuda"><strong>Motivos:</strong> '
            + " · ".join(readiness.motivos_rechazo)
            + "</div>"
        )

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

    componentes.render_html('<div class="seccion-titulo">Incidencias SOMBRA para revisión</div>')

    tipo = st.segmented_control(
        "Tipo de incidencia",
        options=["TODAS", "DIVERGENCIA", "ERROR_SOMBRA"],
        format_func=lambda x: {
            "TODAS": "Todas",
            "DIVERGENCIA": "Divergencias",
            "ERROR_SOMBRA": "Errores",
        }[x],
        default="TODAS",
        key="sombra_incidencias_tipo",
    )

    tipo_consulta = None if tipo == "TODAS" else tipo
    incidencias = ServicioMetricasSombraV3(db).observaciones(
        prestamo_id=prestamo_id,
        tipo=tipo_consulta,
        limite=100,
    )

    if not incidencias:
        componentes.render_html(
            '<div class="nota-contextual nota-success">'
            '<span class="nota-icono">✓</span>'
            '<span class="nota-texto">No hay incidencias del tipo seleccionado.</span>'
            '</div>'
        )
    else:
        filas = []
        for incidencia in incidencias:
            filas.append([
                str(incidencia["id"]),
                str(incidencia["creado_en"]),
                str(incidencia["prestamo_id"]),
                str(incidencia["pago_legacy_id"] or "—"),
                str(incidencia["tipo"]),
                str(incidencia["fingerprint"])[:12],
                str(incidencia["resumen"] or "—"),
            ])
        componentes.tabla(
            [
                {"texto": "ID"},
                {"texto": "Fecha"},
                {"texto": "Préstamo"},
                {"texto": "Pago"},
                {"texto": "Tipo"},
                {"texto": "Fingerprint"},
                {"texto": "Resumen"},
            ],
            filas,
        )

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
