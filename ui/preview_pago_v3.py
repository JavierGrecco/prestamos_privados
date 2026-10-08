"""Presentación del preview canónico de pagos V3."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st

from aplicacion.consultas.preview_pago_v3 import PreviewPagoV3

from . import componentes


def _pesos(valor: Decimal) -> str:
    negativo = valor < 0
    entero, decimales = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{'-' if negativo else ''}$ {entero},{decimales}"


def _render_plan(preview: PreviewPagoV3) -> None:
    plan = preview.plan

    componentes.render_html(
        '<div class="seccion-titulo">Preview canónico del Motor V3</div>'
    )
    componentes.render_html(
        '<div class="nota-contextual nota-info">'
        '<span class="nota-icono">◌</span>'
        '<span class="nota-texto">'
        'Este cálculo no modifica la base. Es el mismo PlanPago V3 que la ruta '
        'de registro utilizará al confirmar.'
        '</span></div>'
    )

    st.session_state["pago_revision_preview"] = plan.revision_prestamo

    if preview.politica_pago_version is not None:
        nombres = {
            "MORA": "Mora",
            "INTERES": "Interés",
            "CAPITAL": "Capital",
        }
        orden = " → ".join(
            nombres.get(concepto, concepto.title())
            for concepto in preview.politica_pago_orden
        )
        componentes.render_html(
            '<div class="nota-contextual nota-info">'
            '<span class="nota-icono">✓</span>'
            '<span class="nota-texto">'
            f'<strong>Regla aplicada:</strong> política v{preview.politica_pago_version}'
            f' · {componentes.escapar_texto_html(orden)}. '
            'La regla surge del préstamo y queda registrada con el pago.'
            '</span></div>'
        )

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Recibido", _pesos(plan.monto_pago_recibido))
    with c2:
        st.metric("Aplicado", _pesos(plan.monto_aplicado))
    with c3:
        st.metric("Excedente", _pesos(plan.excedente.monto))
    with c4:
        st.metric("Tipo", plan.tipo.value)
    with c5:
        st.metric("Revisión", str(plan.revision_prestamo))

    if plan.obligaciones_afectadas:
        componentes.render_html(
            '<div class="seccion-titulo">Cuotas afectadas</div>'
        )
        filas_afectadas = [
            [
                str(obligacion.cuota_id),
                str(obligacion.numero_cuota),
                obligacion.estado_anterior,
                obligacion.estado_posterior,
                _pesos(obligacion.saldo_anterior.total),
                _pesos(obligacion.saldo_posterior.total),
            ]
            for obligacion in plan.obligaciones_afectadas
        ]
        componentes.tabla(
            [
                {"texto": "ID"},
                {"texto": "Cuota"},
                {"texto": "Estado anterior"},
                {"texto": "Estado posterior"},
                {"texto": "Saldo anterior", "alineacion": "der"},
                {"texto": "Saldo posterior", "alineacion": "der"},
            ],
            filas_afectadas,
        )

    if plan.aplicaciones:
        filas = []
        for aplicacion in plan.aplicaciones:
            filas.append([
                str(aplicacion.cuota_id),
                aplicacion.concepto.value,
                aplicacion.origen.value,
                _pesos(aplicacion.monto),
            ])
        componentes.tabla(
            [
                {"texto": "Cuota"},
                {"texto": "Concepto"},
                {"texto": "Origen"},
                {"texto": "Monto", "alineacion": "der"},
            ],
            filas,
        )
    else:
        componentes.render_html(
            '<div class="nota-contextual nota-warning">'
            '<span class="nota-icono">⚠</span>'
            '<span class="nota-texto">El plan no tiene imputaciones.</span>'
            '</div>'
        )

    devengamientos = [
        d
        for eventos in preview.resultado_plan.devengamientos_nuevos.values()
        for d in eventos
    ]
    if devengamientos:
        componentes.render_html(
            '<div class="seccion-titulo">Devengamientos nuevos</div>'
        )
        filas = []
        for cuota_id, eventos in preview.resultado_plan.devengamientos_nuevos.items():
            for d in eventos:
                filas.append([
                    str(cuota_id),
                    d.concepto.value,
                    _pesos(d.monto),
                    d.fecha_desde.strftime("%d/%m/%Y"),
                    d.fecha_hasta.strftime("%d/%m/%Y"),
                ])
        componentes.tabla(
            [
                {"texto": "Cuota"},
                {"texto": "Concepto"},
                {"texto": "Monto", "alineacion": "der"},
                {"texto": "Desde"},
                {"texto": "Hasta"},
            ],
            filas,
        )

    if plan.excedente.monto > Decimal("0.00"):
        if preview.plan_adelanto is None:
            componentes.render_html(
                '<div class="nota-contextual nota-warning">'
                '<span class="nota-icono">⚠</span>'
                '<span class="nota-texto">'
                'El excedente debe resolverse explícitamente como RAI o RNI.'
                '</span></div>'
            )
        else:
            adelanto = preview.plan_adelanto
            componentes.render_html(
                f'<div class="tarjeta-porque tarjeta-grande">'
                f'<div class="icono">↗</div>'
                f'<div class="texto">'
                f'<div class="titulo">Adelanto {componentes.escapar_texto_html(adelanto.tipo.value)}</div>'
                f'<div class="detalle">'
                f'<div class="linea-detalle"><span>Capital antes</span>'
                f'<span>{_pesos(adelanto.capital_antes)}</span></div>'
                f'<div class="linea-detalle"><span>Capital después</span>'
                f'<span>{_pesos(adelanto.capital_despues)}</span></div>'
                f'<div class="linea-detalle"><span>Ahorro de intereses</span>'
                f'<span>{_pesos(adelanto.intereses_ahorrados)}</span></div>'
                f'<div class="linea-detalle"><span>Cuotas</span>'
                f'<span>{adelanto.cuotas_antes} → {adelanto.cuotas_despues}</span></div>'
                f'</div></div></div>'
            )


def _render_comparacion(preview: PreviewPagoV3) -> None:
    comparacion = preview.comparacion_legacy
    if comparacion is None:
        return

    etiquetas = {
        "DEUDA_TOTAL": "deuda total",
        "MORA": "mora",
        "INTERES": "interés",
        "CAPITAL": "capital",
        "EXCEDENTE": "excedente",
    }

    componentes.render_html(
        '<div class="seccion-titulo">Comparación con preview histórico</div>'
    )

    if comparacion.coincidente:
        componentes.render_html(
            '<div class="nota-contextual nota-success">'
            '<span class="nota-icono">✓</span>'
            '<span class="nota-texto">'
            'El preview V3 coincide con el cálculo histórico en los importes comparados.'
            '</span></div>'
        )
        return

    filas = [
        [
            "Deuda total",
            _pesos(comparacion.total_deuda_legacy),
            _pesos(comparacion.total_deuda_v3),
            _pesos(comparacion.diferencia_total_deuda),
        ],
        [
            "Mora aplicada",
            _pesos(comparacion.mora_legacy),
            _pesos(comparacion.mora_v3),
            _pesos(comparacion.mora_v3 - comparacion.mora_legacy),
        ],
        [
            "Interés aplicado",
            _pesos(comparacion.interes_legacy),
            _pesos(comparacion.interes_v3),
            _pesos(comparacion.interes_v3 - comparacion.interes_legacy),
        ],
        [
            "Capital aplicado",
            _pesos(comparacion.capital_legacy),
            _pesos(comparacion.capital_v3),
            _pesos(comparacion.capital_v3 - comparacion.capital_legacy),
        ],
        [
            "Excedente",
            _pesos(comparacion.excedente_legacy),
            _pesos(comparacion.excedente_v3),
            _pesos(comparacion.excedente_v3 - comparacion.excedente_legacy),
        ],
    ]
    componentes.tabla(
        [
            {"texto": "Concepto"},
            {"texto": "Histórico", "alineacion": "der"},
            {"texto": "V3", "alineacion": "der"},
            {"texto": "Diferencia", "alineacion": "der"},
        ],
        filas,
    )
    diferentes = ", ".join(
        etiquetas.get(codigo, codigo.lower())
        for codigo in comparacion.diferencias
    ) or "un concepto no identificado"
    componentes.render_html(
        '<div class="nota-contextual nota-warning">'
        '<span class="nota-icono">⚠</span>'
        '<span class="nota-texto">'
        f'Existe una divergencia en: <strong>{componentes.escapar_texto_html(diferentes)}</strong>. '
        'Se muestra a propósito y no se utiliza para alterar silenciosamente '
        'ninguno de los dos resultados.'
        '</span></div>'
    )


def renderizar_preview_pago_v3(preview: PreviewPagoV3) -> bool:
    """Renderiza un preview ya calculado por la fachada de aplicación."""
    _render_plan(preview)
    _render_comparacion(preview)

    return (
        preview.plan_adelanto is not None
        or preview.plan.excedente.monto == Decimal("0.00")
    )
