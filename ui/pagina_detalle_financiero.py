"""Detalle financiero profundo del préstamo."""

from __future__ import annotations

from decimal import Decimal

import streamlit as st

from aplicacion.consultas.detalle_financiero_prestamo import (
    DetalleFinancieroPrestamo,
    ServicioDetalleFinancieroPrestamo,
)
from aplicacion.servicios.exportaciones import ServicioExportaciones
from dominio.excepciones import ErrorInvariante, ErrorValidacion
from . import componentes


def _pesos(valor) -> str:
    valor = Decimal(str(valor))
    negativo = valor < 0
    entero, decimales = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{'-' if negativo else ''}$ {entero},{decimales}"


def _render_resumen(detalle: DetalleFinancieroPrestamo) -> None:
    r = detalle.resumen

    componentes.render_html('<div class="seccion-titulo">Capital</div>')
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Capital original", _pesos(r.capital_original))
    with c2:
        st.metric("Capital aplicado", _pesos(r.capital_aplicado))
    with c3:
        st.metric("Capital pendiente", _pesos(r.capital_pendiente))
    with c4:
        st.metric("Amortizado", f"{r.porcentaje_amortizado:.2f}%")

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Interés devengado", _pesos(r.interes_devengado))
    with c2:
        st.metric(
            "Intereses ahorrados por recálculos",
            _pesos(r.interes_ahorrado_por_recalculos),
        )


def _render_amortizacion(detalle: DetalleFinancieroPrestamo) -> None:
    componentes.render_html('<div class="seccion-titulo">Amortización vigente</div>')
    if not detalle.cuotas:
        componentes.render_html(
            '<div class="nota-contextual nota-info">'
            '<span class="nota-icono">◌</span>'
            '<span class="nota-texto">No hay cuotas en la versión activa.</span>'
            '</div>'
        )
        return

    filas = []
    for cuota in detalle.cuotas:
        estado = cuota.estado
        if cuota.fue_recalculada:
            estado += " · recalculada"
        if cuota.tuvo_pago_parcial:
            estado += " · parcial"

        filas.append([
            str(cuota.numero),
            cuota.vencimiento.strftime("%d/%m/%Y"),
            estado,
            _pesos(cuota.capital_inicial),
            _pesos(cuota.interes_teorico),
            _pesos(cuota.capital_teorico),
            _pesos(cuota.cuota_teorica),
            _pesos(cuota.saldo_teorico),
            _pesos(cuota.capital_pendiente),
        ])

    componentes.tabla(
        [
            {"texto": "#"},
            {"texto": "Vencimiento"},
            {"texto": "Estado"},
            {"texto": "Capital inicial", "alineacion": "der"},
            {"texto": "Interés", "alineacion": "der"},
            {"texto": "Capital", "alineacion": "der"},
            {"texto": "Cuota", "alineacion": "der"},
            {"texto": "Saldo teórico", "alineacion": "der"},
            {"texto": "Capital pendiente", "alineacion": "der"},
        ],
        filas,
    )


def _render_trayectoria(detalle: DetalleFinancieroPrestamo) -> None:
    componentes.render_html('<div class="seccion-titulo">Evolución del capital</div>')
    puntos = detalle.resumen.trayectoria.puntos

    if not puntos:
        return

    filas = []
    for punto in puntos:
        filas.append([
            punto.fecha.strftime("%d/%m/%Y"),
            _pesos(punto.capital),
            punto.referencia or "—",
        ])

    componentes.tabla(
        [
            {"texto": "Fecha"},
            {"texto": "Capital pendiente", "alineacion": "der"},
            {"texto": "Referencia"},
        ],
        filas,
    )

    componentes.render_html(
        '<div class="nota-contextual nota-info">'
        '<span class="nota-icono">ℹ</span>'
        '<span class="nota-texto">'
        'La trayectoria se reconstruye a partir de las aplicaciones de capital '
        'persistidas en pagos válidos. No reinterpreta pagos históricos.'
        '</span></div>'
    )


def _render_devengamientos(detalle: DetalleFinancieroPrestamo) -> None:
    componentes.render_html('<div class="seccion-titulo">Devengamientos</div>')
    if not detalle.devengamientos:
        componentes.render_html(
            '<div class="estado-vacio-chico">No hay devengamientos persistidos.</div>'
        )
        return

    filas = [
        [
            str(d.id),
            "—" if d.cuota_id is None else str(d.cuota_id),
            d.concepto,
            _pesos(d.monto),
            d.fecha_desde.strftime("%d/%m/%Y"),
            d.fecha_hasta.strftime("%d/%m/%Y"),
            d.origen,
            d.motor_version,
        ]
        for d in detalle.devengamientos
    ]

    componentes.tabla(
        [
            {"texto": "ID"},
            {"texto": "Cuota"},
            {"texto": "Concepto"},
            {"texto": "Monto", "alineacion": "der"},
            {"texto": "Desde"},
            {"texto": "Hasta"},
            {"texto": "Origen"},
            {"texto": "Motor"},
        ],
        filas,
    )


def _render_recalculos(detalle: DetalleFinancieroPrestamo) -> None:
    componentes.render_html('<div class="seccion-titulo">Recálculos RAI/RNI</div>')
    if not detalle.recalculos:
        componentes.render_html(
            '<div class="estado-vacio-chico">No hay recálculos registrados.</div>'
        )
        return

    for rec in detalle.recalculos:
        componentes.render_html(
            f'<div class="tarjeta-porque">'
            f'<div class="icono">↗</div>'
            f'<div class="texto">'
            f'<div class="titulo">{rec.tipo} · {rec.fecha.strftime("%d/%m/%Y")} · pago #{rec.pago_id}</div>'
            f'<div class="detalle">'
            f'<div class="linea-detalle"><span>Capital</span>'
            f'<span>{_pesos(rec.capital_antes)} → {_pesos(rec.capital_despues)}</span></div>'
            f'<div class="linea-detalle"><span>Cuotas</span>'
            f'<span>{rec.cuotas_antes} → {rec.cuotas_despues}</span></div>'
            f'<div class="linea-detalle"><span>Intereses</span>'
            f'<span>{_pesos(rec.intereses_antes)} → {_pesos(rec.intereses_despues)}</span></div>'
            f'<div class="linea-detalle"><span>Ahorro</span>'
            f'<span>{_pesos(rec.ahorro_intereses)}</span></div>'
            f'</div></div></div>'
        )


def _render_eventos_capital(detalle: DetalleFinancieroPrestamo) -> None:
    componentes.render_html('<div class="seccion-titulo">Aplicaciones de capital</div>')
    if not detalle.eventos_capital:
        componentes.render_html(
            '<div class="estado-vacio-chico">Todavía no hay reducciones de capital registradas.</div>'
        )
        return

    filas = [
        [
            str(e.pago_id),
            e.fecha.strftime("%d/%m/%Y"),
            e.tipo_pago,
            _pesos(e.monto),
            e.referencia,
        ]
        for e in detalle.eventos_capital
    ]
    componentes.tabla(
        [
            {"texto": "Pago"},
            {"texto": "Fecha"},
            {"texto": "Tipo"},
            {"texto": "Capital", "alineacion": "der"},
            {"texto": "Referencia"},
        ],
        filas,
    )


def render(db, prestamo_id: int) -> None:
    try:
        detalle = ServicioDetalleFinancieroPrestamo(db).obtener(prestamo_id)
    except (ErrorInvariante, ErrorValidacion, ValueError) as exc:
        componentes.render_html(
            f'<div class="nota-contextual nota-warning">'
            f'<span class="nota-icono">⚠</span>'
            f'<span class="nota-texto">{exc}</span>'
            f'</div>'
        )
        return

    if st.button("← Volver al préstamo", key="volver_detalle_financiero"):
        st.session_state["pagina_pendiente"] = "prestamos"
        st.rerun()

    componentes.render_html(
        f'<div class="detalle-titulo">Detalle financiero</div>'
        f'<div class="saludo">{detalle.prestamo_numero}</div>'
    )

    st.download_button(
        "Descargar amortización CSV",
        data=ServicioExportaciones(db).amortizacion_csv(prestamo_id).encode("utf-8-sig"),
        file_name=f"amortizacion-{detalle.prestamo_numero}.csv",
        mime="text/csv",
        key=f"detalle_exportar_amortizacion_{prestamo_id}",
        use_container_width=True,
    )

    _render_resumen(detalle)

    tabs = st.tabs(["Amortización", "Capital", "Devengamientos", "Recálculos"])
    with tabs[0]:
        _render_amortizacion(detalle)
    with tabs[1]:
        _render_trayectoria(detalle)
        _render_eventos_capital(detalle)
    with tabs[2]:
        _render_devengamientos(detalle)
    with tabs[3]:
        _render_recalculos(detalle)
