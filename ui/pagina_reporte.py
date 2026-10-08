"""Pantalla de reporte financiero personal.

Compone los read models existentes y permite descargar una copia CSV estructurada.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st

from aplicacion.consultas.reporte_financiero_persona import (
    ServicioReporteFinancieroPersona,
)
from aplicacion.servicios.exportaciones import ServicioExportaciones
from infraestructura.db import BaseDatos

from . import componentes


def _pesos(valor: Decimal) -> str:
    negativo = valor < Decimal("0")
    entero, decimales = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{'-' if negativo else ''}$ {entero},{decimales}"


def render(db: BaseDatos, persona_id: int) -> None:
    st.title("Reporte")
    st.caption(
        "Una vista única de tu posición, movimientos, planificación, escenarios y rendimiento."
    )

    c1, c2 = st.columns(2)
    with c1:
        horizonte = st.selectbox(
            "Horizonte futuro",
            options=[3, 6, 12, 24, 36],
            index=2,
            key="reporte_horizonte",
        )
    with c2:
        fecha_corte = st.date_input(
            "Fecha de corte",
            value=date.today(),
            key="reporte_fecha_corte",
        )

    inflacion_pct = st.number_input(
        "Inflación mensual supuesta para resultados reales (%)",
        min_value=-99.0,
        max_value=100.0,
        value=5.0,
        step=0.5,
        key="reporte_inflacion",
    )
    inflacion = Decimal(str(inflacion_pct)) / Decimal("100")

    try:
        reporte = ServicioReporteFinancieroPersona(db).obtener(
            persona_id,
            fecha_corte=fecha_corte,
            inflacion_mensual_supuesta=inflacion,
            horizonte_meses=horizonte,
        )
        csv = ServicioExportaciones(db).reporte_financiero_persona_csv(
            persona_id,
            fecha_corte=fecha_corte,
            inflacion_mensual_supuesta=inflacion,
            horizonte_meses=horizonte,
        )
    except ValueError as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    componentes.nota_contextual(
        (
            f"Reporte de {reporte.nombre_persona}. Corte: "
            f"{reporte.fecha_corte:%d/%m/%Y}. Los datos reales y estimados "
            "se mantienen separados."
        ),
        "info",
    )

    st.subheader("Posición")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Capital invertido", _pesos(reporte.posicion.capital_invertido))
    with c2:
        st.metric(
            "Capital pendiente de deuda",
            _pesos(reporte.posicion.capital_deuda_pendiente),
        )
    with c3:
        st.metric(
            "Posición neta de capital",
            _pesos(reporte.posicion.posicion_neta_capital),
        )

    st.subheader("Movimientos reales")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Cobros", _pesos(reporte.posicion.cobros_reales))
    with c2:
        st.metric("Pagos", _pesos(reporte.posicion.pagos_reales))
    with c3:
        st.metric("Neto real", _pesos(reporte.posicion.flujo_neto_real))

    st.subheader("Plan futuro")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            "Cobros estimados",
            _pesos(reporte.planificacion.cobros_estimados_total),
        )
    with c2:
        st.metric(
            "Pagos estimados",
            _pesos(reporte.planificacion.pagos_estimados_total),
        )
    with c3:
        st.metric(
            "Resultado futuro estimado",
            _pesos(reporte.planificacion.neto_estimado_total),
        )

    st.subheader("Escenarios")
    for escenario in reporte.escenarios.resultados:
        st.markdown(
            f"**{escenario.nombre}** — inflación mensual "
            f"{escenario.inflacion_mensual * 100:.2f}% · "
            f"devaluación mensual {escenario.devaluacion_mensual * 100:.2f}% · "
            f"neto a precios de hoy {_pesos(escenario.neto_real)}"
        )

    st.subheader("Rendimiento")
    if reporte.rendimiento.inversor is not None:
        indicador = reporte.rendimiento.inversor
        st.markdown(
            f"**Inversión:** "
            f"{_pct(indicador.valor)} "
            f"({indicador.cantidad_flujos_reales} movimientos reales)"
        )
    if reporte.rendimiento.deudor is not None:
        indicador = reporte.rendimiento.deudor
        st.markdown(
            f"**Deuda:** "
            f"{_pct(indicador.valor)} "
            f"({indicador.cantidad_flujos_reales} movimientos reales)"
        )
    if (
        reporte.rendimiento.inversor is None
        and reporte.rendimiento.deudor is None
    ):
        st.write("Todavía no hay movimientos reales suficientes para mostrar rendimiento.")

    st.divider()
    st.subheader("Descarga")
    st.caption(
        "El CSV incluye contexto, datos reales, estimaciones, supuestos y escenarios. "
        "Tratale como información financiera sensible."
    )
    st.download_button(
        "Descargar reporte CSV",
        data=csv.encode("utf-8-sig"),
        file_name=f"reporte_financiero_{persona_id}_{fecha_corte.isoformat()}.csv",
        mime="text/csv",
        key="reporte_financiero_descargar_csv",
    )

    with st.expander("Qué incluye y qué no"):
        st.markdown(
            """
El reporte usa solamente información registrada en Préstamos Privados.

No agrega patrimonio externo, sueldo, gastos personales, efectivo ni otros
activos o deudas que el sistema no conozca.

Los datos reales describen hechos registrados. Los datos estimados y los
escenarios muestran cálculos sobre el futuro conocido y supuestos elegidos.
"""
        )


def _pct(valor: Decimal | None) -> str:
    if valor is None:
        return "Todavía no disponible"
    return f"{valor * Decimal('100'):.2f}%"
