"""Pantalla de rendimiento financiero explicado."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st

from aplicacion.consultas.rendimiento_financiero_persona import (
    IndicadorRendimiento,
    ServicioRendimientoFinancieroPersona,
)
from infraestructura.db import BaseDatos

from . import componentes


def _pct(valor: Decimal | None) -> str:
    if valor is None:
        return "No disponible"
    return f"{valor * Decimal('100'):.2f}%"


def _fecha(fecha: date | None) -> str:
    return fecha.strftime("%d/%m/%Y") if fecha else "—"


def _render_indicador(indicador: IndicadorRendimiento) -> None:
    titulo = "Tu inversión" if indicador.rol == "INVERSOR" else "Tu deuda"
    st.subheader(titulo)

    if not indicador.disponible:
        componentes.nota_contextual(
            "Todavía no podemos calcular una tasa anualizada de forma confiable con los movimientos registrados.",
            "info",
        )
        st.write(indicador.explicacion)
    else:
        st.metric(indicador.nombre, _pct(indicador.valor))
        st.write(indicador.explicacion)

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Movimientos reales", str(indicador.cantidad_flujos_reales))
    with c2:
        st.metric(
            "Período",
            f"{_fecha(indicador.fecha_desde)} a {_fecha(indicador.fecha_hasta)}",
        )

    if indicador.disponible and indicador.rendimiento_real is not None:
        st.metric(
            "Resultado ajustado por inflación",
            _pct(indicador.rendimiento_real),
        )
        st.caption(
            "Usa el supuesto de inflación elegido. "
            "No cambia los movimientos reales registrados."
        )

    if indicador.disponible:
        if indicador.valor_usd is not None:
            st.metric("Tasa anualizada en USD", _pct(indicador.valor_usd))
            st.caption(
                "Disponible porque todos los flujos necesarios tienen referencia USD."
            )
        else:
            componentes.nota_contextual(
                "La tasa en USD no está disponible porque falta una referencia USD completa para los flujos reales.",
                "info",
            )

    with st.expander("¿Cómo se calculó?"):
        st.markdown(
            """
El rendimiento anualizado usa los movimientos reales registrados y sus fechas.

Para un inversor, representa la tasa anualizada que iguala el dinero aportado
con el dinero cobrado.

Para un deudor, representa el costo anualizado implícito entre el dinero
recibido y los pagos registrados.

El ajuste por inflación sirve para responder cuánto representa ese resultado
en términos de poder de compra, según el supuesto elegido.
"""
        )


def render(db: BaseDatos, persona_id: int) -> None:
    st.title("Rendimiento")
    st.caption(
        "Qué rendimiento o costo muestran los movimientos que realmente ocurrieron."
    )

    inflacion_pct = st.number_input(
        "Inflación mensual supuesta para el cálculo real (%)",
        min_value=-99.0,
        max_value=100.0,
        value=5.0,
        step=0.5,
        key="rendimiento_inflacion",
    )
    fecha_corte = st.date_input(
        "Fecha de corte",
        value=date.today(),
        key="rendimiento_fecha_corte",
    )

    try:
        resultado = ServicioRendimientoFinancieroPersona(db).obtener(
            persona_id,
            fecha_corte=fecha_corte,
            inflacion_mensual_supuesto=(
                Decimal(str(inflacion_pct)) / Decimal("100")
            ),
        )
    except ValueError as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    componentes.nota_contextual(
        (
            f"Las tasas de esta pantalla usan movimientos reales hasta "
            f"{_fecha(fecha_corte)}. Lo futuro se analiza por separado en Escenarios."
        ),
        "info",
    )

    if resultado.inversor is not None:
        _render_indicador(resultado.inversor)

    if resultado.deudor is not None:
        _render_indicador(resultado.deudor)

    if resultado.inversor is None and resultado.deudor is None:
        componentes.estado_vacio(
            "📈",
            "Todavía no hay una posición con movimientos reales",
            "Cuando existan inversiones o préstamos registrados, vas a poder consultar su rendimiento o costo.",
        )

    if resultado.advertencias:
        with st.expander("Observaciones del cálculo"):
            for advertencia in resultado.advertencias:
                st.warning(advertencia)

    with st.expander("Importante antes de tomar una decisión"):
        st.markdown(
            """
Una tasa histórica no garantiza que el futuro vaya a repetir ese resultado.

Una tasa no disponible no significa que la inversión haya salido mal. Puede
significar simplemente que todavía no existen movimientos suficientes para
calcularla correctamente.

Las métricas de esta pantalla no agregan ingresos, gastos ni información que
el sistema no tenga registrada.
"""
        )
