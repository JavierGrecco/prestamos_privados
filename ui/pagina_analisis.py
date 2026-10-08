"""Dashboard financiero funcional para la UI."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st

from aplicacion.consultas.analisis_financiero import (
    ResultadoAnalisisFinanciero,
    ServicioAnalisisFinanciero,
)
from infraestructura.repositorios import ParticipacionRepo, PrestamoRepo
from . import componentes


def _pesos(valor: Decimal) -> str:
    negativo = valor < 0
    entero, decimales = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{'-' if negativo else ''}$ {entero},{decimales}"


def _pct(valor: Decimal | None) -> str:
    if valor is None:
        return "—"
    return f"{valor * Decimal('100'):.2f}%"


def _fecha(valor: date) -> str:
    return valor.strftime("%d/%m/%Y")


def _render_resumen(resultado: ResultadoAnalisisFinanciero) -> None:
    resumen = resultado.resumen
    componentes.render_html('<div class="seccion-titulo">Tu posición</div>')

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            "Capital aportado activo",
            _pesos(resumen.capital_aportado_activo),
        )
    with c2:
        st.metric(
            "Capital adeudado",
            _pesos(resumen.capital_deudor_pendiente),
        )
    with c3:
        st.metric(
            "Posición neta de capital",
            _pesos(resumen.posicion_neta_capital),
        )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Cobros inversor", _pesos(resumen.cobros_inversor_reales))
    with c2:
        st.metric("Pagos deudor", _pesos(resumen.pagos_deudor_reales))
    with c3:
        st.metric("XIRR inversor", _pct(resumen.xirr_inversor))
    with c4:
        st.metric("XIRR deuda", _pct(resumen.xirr_deudor))

    c1, c2 = st.columns(2)
    with c1:
        st.metric("XIRR inversor USD", _pct(resumen.xirr_inversor_usd))
    with c2:
        st.metric("XIRR deuda USD", _pct(resumen.xirr_deudor_usd))

    if resumen.rendimiento_real_inversor is not None:
        componentes.render_html(
            f'<div class="detalle-item"><span>Rendimiento real inversor</span>'
            f'<strong>{_pct(resumen.rendimiento_real_inversor)}</strong></div>'
        )
    if resumen.rendimiento_real_deudor is not None:
        componentes.render_html(
            f'<div class="detalle-item"><span>Costo real de la deuda</span>'
            f'<strong>{_pct(resumen.rendimiento_real_deudor)}</strong></div>'
        )

    componentes.render_html(
        '<div class="nota-contextual nota-info">'
        '<span class="nota-icono">ℹ</span>'
        '<span class="nota-texto">'
        'La posición neta de capital es una exposición contractual: no incluye '
        'dinero disponible fuera de estos préstamos ni valuaciones de mercado.'
        '</span></div>'
    )


def _render_cashflow(resultado: ResultadoAnalisisFinanciero) -> None:
    componentes.render_html('<div class="seccion-titulo">Cashflow</div>')

    filtro = st.segmented_control(
        "Cashflow",
        options=["Todos", "Reales", "Proyectados"],
        default="Todos",
        label_visibility="collapsed",
        key="analisis_filtro_cashflow",
    )

    if filtro == "Reales":
        flujos = resultado.flujos_reales
    elif filtro == "Proyectados":
        flujos = resultado.flujos_proyectados
    else:
        flujos = tuple(
            sorted(
                (*resultado.flujos_reales, *resultado.flujos_proyectados),
                key=lambda f: (f.fecha, f.prestamo_id, f.tipo),
            )
        )

    if not flujos:
        componentes.render_html(
            '<div class="nota-contextual nota-info">'
            '<span class="nota-icono">◌</span>'
            '<span class="nota-texto">No hay flujos para mostrar.</span>'
            '</div>'
        )
        return

    filas = []
    for flujo in flujos:
        filas.append([
            _fecha(flujo.fecha),
            flujo.rol,
            flujo.tipo,
            flujo.prestamo_numero,
            "Real" if flujo.real else "Proyectado",
            _pesos(flujo.monto_ars),
            "—" if flujo.monto_usd is None else f"USD {flujo.monto_usd:,.2f}",
        ])

    componentes.tabla(
        [
            {"texto": "Fecha"},
            {"texto": "Rol"},
            {"texto": "Tipo"},
            {"texto": "Préstamo"},
            {"texto": "Naturaleza"},
            {"texto": "ARS", "alineacion": "der"},
            {"texto": "USD", "alineacion": "der"},
        ],
        filas,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Entradas reales", _pesos(resultado.entradas_reales))
    with c2:
        st.metric("Salidas reales", _pesos(resultado.salidas_reales))
    with c3:
        st.metric("Neto real", _pesos(resultado.neto_real))

    if resultado.flujos_proyectados:
        componentes.render_html(
            f'<div class="detalle-item"><span>Valor real de flujos proyectados'
            f' bajo el supuesto de inflación</span>'
            f'<strong>{_pesos(resultado.valor_real_proyectado)}</strong></div>'
        )


def _render_advertencias(resultado: ResultadoAnalisisFinanciero) -> None:
    if not resultado.advertencias:
        return

    componentes.render_html('<div class="seccion-titulo">Observaciones</div>')
    for advertencia in resultado.advertencias:
        componentes.render_html(
            f'<div class="nota-contextual nota-warning">'
            f'<span class="nota-icono">⚠</span>'
            f'<span class="nota-texto">{advertencia}</span>'
            f'</div>'
        )


def _prestamos_para_persona(db, persona_id: int) -> list:
    repo = PrestamoRepo(db)
    participaciones = ParticipacionRepo(db).por_inversor(persona_id)

    ids = set()
    resultado = []
    for prestamo in repo.listar(deudor_id=persona_id):
        if prestamo.estado in ("ACTIVO", "EN_MORA") and prestamo.id not in ids:
            ids.add(prestamo.id)
            resultado.append(prestamo)

    for participacion in participaciones:
        if participacion.estado != "ACTIVA" or participacion.prestamo_id in ids:
            continue
        prestamo = repo.obtener(participacion.prestamo_id)
        if prestamo is not None and prestamo.estado in ("ACTIVO", "EN_MORA"):
            ids.add(prestamo.id)
            resultado.append(prestamo)

    return sorted(resultado, key=lambda p: (p.fecha_inicio or date.min, p.id or 0), reverse=True)


def _render_escenarios(db, persona_id: int) -> None:
    componentes.render_html('<div class="seccion-titulo">Escenarios macroeconómicos</div>')

    prestamos = _prestamos_para_persona(db, persona_id)
    if not prestamos:
        componentes.render_html(
            '<div class="nota-contextual nota-info">'
            '<span class="nota-icono">◌</span>'
            '<span class="nota-texto">No hay préstamos activos para simular.</span>'
            '</div>'
        )
        return

    opciones = {p.id: f"{p.numero} — {p.destino or 'sin destino'}" for p in prestamos}
    ids = list(opciones)
    seleccionado = st.selectbox(
        "Préstamo",
        options=ids,
        format_func=lambda x: opciones[x],
        label_visibility="collapsed",
        key="analisis_prestamo_escenario",
    )

    resultado = ServicioAnalisisFinanciero(db).escenarios_para_prestamo(seleccionado)

    for escenario in resultado.resultados:
        componentes.render_html(
            f'<div class="tarjeta-porque">'
            f'<div class="icono">📊</div>'
            f'<div class="texto">'
            f'<div class="titulo">{escenario.escenario.nombre}</div>'
            f'<div class="detalle">{escenario.escenario.descripcion}</div>'
            f'<div class="linea-detalle"><span>Inflación mensual</span>'
            f'<span>{escenario.escenario.inflacion_mensual * 100:.1f}%</span></div>'
            f'<div class="linea-detalle"><span>Devaluación mensual</span>'
            f'<span>{escenario.escenario.devaluacion_mensual * 100:.1f}%</span></div>'
            f'<div class="linea-detalle"><span>Cuota final real</span>'
            f'<span>{_pesos(escenario.cuota_final_real)}</span></div>'
            f'<div class="linea-detalle"><span>Cuota final USD</span>'
            f'<span>USD {escenario.cuota_final_usd:,.2f}</span></div>'
            f'<div class="linea-detalle"><span>Pérdida de poder de compra</span>'
            f'<span>{escenario.perdida_poder_compra_pct:.2f}%</span></div>'
            f'</div></div>'
        )


def render(db, persona_id: int) -> None:
    componentes.render_html('<div class="detalle-titulo">Análisis financiero</div>')
    componentes.render_html(
        '<div class="saludo">Cashflow, posición, rendimiento y poder de compra</div>'
    )

    c1, c2 = st.columns(2)
    with c1:
        inflacion_pct = st.number_input(
            "Inflación mensual supuesta (%)",
            min_value=-99.0,
            max_value=100.0,
            value=5.0,
            step=0.5,
            format="%.2f",
            key="analisis_inflacion",
        )
    with c2:
        fecha_corte = st.date_input(
            "Fecha de corte",
            value=date.today(),
            key="analisis_fecha_corte",
        )

    inflacion = Decimal(str(inflacion_pct)) / Decimal("100")
    resultado = ServicioAnalisisFinanciero(db).obtener(
        persona_id,
        fecha_corte=fecha_corte,
        inflacion_mensual_supuesto=inflacion,
    )

    componentes.render_html(
        f'<div class="nota-contextual nota-info">'
        f'<span class="nota-icono">ℹ</span>'
        f'<span class="nota-texto">'
        f'Fecha de corte: {_fecha(fecha_corte)}. Inflación mensual usada: '
        f'{inflacion_pct:.2f}%. Es un supuesto para convertir valores futuros '
        f'a poder de compra de hoy; no es un dato automático del INDEC.'
        f'</span></div>'
    )

    _render_resumen(resultado)
    _render_cashflow(resultado)
    _render_advertencias(resultado)
    _render_escenarios(db, persona_id)
