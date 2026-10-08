"""Presentación del preview canónico de pagos V3."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st

from aplicacion.consultas.preview_pago_v3 import (
    PreviewPagoV3,
    ServicioPreviewPagoV3,
)
from dominio.excepciones import ErrorInvariante, ErrorValidacion

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

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Recibido", _pesos(plan.monto_pago_recibido))
    with c2:
        st.metric("Aplicado", _pesos(plan.monto_aplicado))
    with c3:
        st.metric("Excedente", _pesos(plan.excedente.monto))
    with c4:
        st.metric("Tipo", plan.tipo.value)

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
        filas = [
            [
                str(d.cuota_id) if hasattr(d, "cuota_id") else "—",
                d.concepto.value,
                _pesos(d.monto),
                d.fecha_desde.strftime("%d/%m/%Y"),
                d.fecha_hasta.strftime("%d/%m/%Y"),
            ]
            for d in devengamientos
        ]
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
                f'<div class="titulo">Adelanto {adelanto.tipo.value}</div>'
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
    componentes.render_html(
        '<div class="nota-contextual nota-warning">'
        '<span class="nota-icono">⚠</span>'
        '<span class="nota-texto">'
        'Existe una divergencia. Se muestra a propósito y no se utiliza para '
        'alterar silenciosamente ninguno de los dos resultados.'
        '</span></div>'
    )


def renderizar_preview_pago_v3(
    db,
    *,
    prestamo_id: int,
    monto: Decimal,
    fecha_valor: date,
    opcion_adelanto: str | None,
) -> bool:
    """Renderiza el preview y devuelve si es apto para una futura confirmación V3."""
    try:
        preview = ServicioPreviewPagoV3(db).previsualizar(
            prestamo_id=prestamo_id,
            monto=monto,
            fecha_valor=fecha_valor,
            opcion_adelanto=opcion_adelanto,
            comparar_legacy=True,
        )
    except (ErrorInvariante, ErrorValidacion, ValueError) as exc:
        componentes.render_html(
            f'<div class="nota-contextual nota-warning">'
            f'<span class="nota-icono">⚠</span>'
            f'<span class="nota-texto">{exc}</span>'
            f'</div>'
        )
        return False

    _render_plan(preview)
    _render_comparacion(preview)

    return preview.plan_adelanto is not None or preview.plan.excedente.monto == Decimal("0.00")
