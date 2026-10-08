"""Pantalla de reportes financieros por persona."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st

from aplicacion.servicios.reportes_persona import (
    ReportePersona,
    ServicioReportesPersona,
)
from infraestructura.db import BaseDatos

from . import componentes


def render(db: BaseDatos, persona_id: int) -> None:
    st.title("Reportes")
    st.caption(
        "Guardá o compartí una foto clara de tu situación financiera."
    )

    c1, c2 = st.columns(2)
    with c1:
        fecha_corte = st.date_input(
            "Fecha de corte",
            value=date.today(),
            key="reportes_fecha_corte",
        )
    with c2:
        horizonte = st.selectbox(
            "Horizonte futuro",
            options=[3, 6, 12, 24, 36],
            index=2,
            key="reportes_horizonte",
        )

    inflacion_pct = st.number_input(
        "Inflación mensual usada para el rendimiento real (%)",
        min_value=-99.0,
        max_value=100.0,
        value=5.0,
        step=0.5,
        key="reportes_inflacion",
    )

    servicio = ServicioReportesPersona(db)

    try:
        reporte = servicio.obtener(
            persona_id,
            fecha_corte=fecha_corte,
            inflacion_mensual_supuesto=(
                Decimal(str(inflacion_pct)) / Decimal("100")
            ),
            horizonte_meses=horizonte,
        )
    except ValueError as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    componentes.nota_contextual(
        (
            f"Este reporte corresponde a {reporte.nombre} y toma como corte "
            f"el {reporte.fecha_corte:%d/%m/%Y}. Los datos futuros están "
            "marcados como estimados."
        ),
        "info",
    )

    informe = servicio.markdown(reporte)
    datos_json = servicio.json(reporte)
    datos_csv = servicio.csv_resumen(reporte)

    st.subheader("Vista humana")
    st.markdown(informe)

    st.subheader("Descargas")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "Descargar informe",
            data=informe,
            file_name=f"reporte_financiero_{reporte.persona_id}_{reporte.fecha_corte.isoformat()}.md",
            mime="text/markdown",
            key="reporte_descargar_markdown",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "Descargar JSON",
            data=datos_json,
            file_name=f"reporte_financiero_{reporte.persona_id}_{reporte.fecha_corte.isoformat()}.json",
            mime="application/json",
            key="reporte_descargar_json",
            use_container_width=True,
        )
    with c3:
        st.download_button(
            "Descargar CSV resumen",
            data=datos_csv,
            file_name=f"reporte_financiero_{reporte.persona_id}_{reporte.fecha_corte.isoformat()}.csv",
            mime="text/csv",
            key="reporte_descargar_csv",
            use_container_width=True,
        )

    with st.expander("Qué contiene cada formato"):
        st.markdown(
            """
**Informe**  
Es el formato más fácil de leer y compartir con otra persona.

**JSON**  
Incluye la estructura completa de los datos, útil para integraciones o para
un operador que necesite procesarla.

**CSV resumen**  
Incluye los principales indicadores en formato tabular.

Todos los formatos corresponden a la misma fecha de corte y a los mismos
supuestos. Ninguno modifica la base.
"""
        )

    with st.expander("Alcance y límites"):
        st.markdown(
            """
El reporte resume solamente información que existe en Préstamos Privados.

No representa todo tu patrimonio, no conoce tus ingresos o gastos externos y
no constituye asesoramiento financiero.

Los movimientos históricos son hechos registrados. Las cifras futuras son
estimaciones y pueden cambiar cuando cambie el estado real de los préstamos
o inversiones.
"""
        )
