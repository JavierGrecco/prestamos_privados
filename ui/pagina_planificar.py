"""Pantalla de planificación financiera personal.

La pantalla ayuda a responder:
- ¿Cuánto espero cobrar?
- ¿Cuánto espero pagar?
- ¿Habrá algún mes en que necesite una reserva?
- ¿Cómo se distribuyen esos movimientos en el tiempo?

No agrega ingresos/gastos externos que la aplicación no conozca.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import plotly.graph_objects as go
import streamlit as st

from aplicacion.consultas.planificacion_financiera_persona import (
    PlanificacionFinancieraPersona,
    ServicioPlanificacionFinancieraPersona,
)
from infraestructura.db import BaseDatos

from . import componentes


def _pesos(valor: Decimal) -> str:
    negativo = valor < Decimal("0")
    entero, decimales = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{'-' if negativo else ''}$ {entero},{decimales}"


def _fecha(fecha: date) -> str:
    return fecha.strftime("%d/%m/%Y")


def _mensaje_reserva(plan: PlanificacionFinancieraPersona) -> None:
    if plan.reserva_sugerida <= Decimal("0"):
        componentes.nota_contextual(
            (
                "Con los cobros y pagos futuros que conocemos hoy, "
                "no aparece un déficit acumulado durante el horizonte elegido."
            ),
            "success",
        )
        return

    mes = (
        _fecha(plan.mes_mas_exigente.periodo)
        if plan.mes_mas_exigente
        else "el período analizado"
    )
    componentes.nota_contextual(
        (
            f"Para atravesar el peor acumulado proyectado necesitarías "
            f"una reserva de {_pesos(plan.reserva_sugerida)} al inicio del período. "
            f"El mes más exigente es {mes}."
        ),
        "warning",
    )


def _render_resumen(plan: PlanificacionFinancieraPersona) -> None:
    st.subheader("Plan para los próximos meses")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Cobros futuros estimados", _pesos(plan.cobros_estimados_total))
    with c2:
        st.metric("Pagos futuros estimados", _pesos(plan.pagos_estimados_total))
    with c3:
        st.metric("Resultado futuro estimado", _pesos(plan.neto_estimado_total))

    _mensaje_reserva(plan)

    with st.expander("¿Qué significa el resultado futuro?"):
        st.markdown(
            """
Los **cobros futuros estimados** son movimientos de dinero que el sistema
espera según los préstamos e inversiones registrados.

Los **pagos futuros estimados** son obligaciones que el sistema espera según
los préstamos registrados.

El **resultado futuro estimado** es la diferencia:

`cobros futuros - pagos futuros = resultado futuro`

Un resultado positivo no significa que ese dinero esté disponible hoy.
Un resultado negativo tampoco incluye gastos personales que el sistema no
conoce.
"""
        )


def _render_grafico(plan: PlanificacionFinancieraPersona) -> None:
    if not plan.movimientos_mensuales:
        componentes.estado_vacio(
            "📅",
            "Todavía no hay movimientos futuros conocidos",
            "Cuando exista un préstamo o inversión con movimientos futuros, aparecerá acá.",
        )
        return

    labels = [m.periodo.strftime("%m/%Y") for m in plan.movimientos_mensuales]
    netos = [float(m.neto_estimado) for m in plan.movimientos_mensuales]
    acumulados = [float(m.acumulado_estimado) for m in plan.movimientos_mensuales]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=labels, y=netos, name="Movimiento del mes")
    )
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=acumulados,
            mode="lines+markers",
            name="Acumulado",
        )
    )
    fig.update_layout(
        title="Cómo se distribuirían los movimientos",
        xaxis_title="Mes",
        yaxis_title="ARS",
        margin=dict(l=10, r=10, t=50, b=10),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Barras: cobros menos pagos del mes. Línea: acumulado empezando en cero."
    )


def _render_tabla(plan: PlanificacionFinancieraPersona) -> None:
    filas = []
    for movimiento in plan.movimientos_mensuales:
        estado = (
            "Déficit"
            if movimiento.requiere_reserva
            else "Sin déficit acumulado"
        )
        filas.append(
            [
                movimiento.periodo.strftime("%m/%Y"),
                _pesos(movimiento.cobros_estimados),
                _pesos(movimiento.pagos_estimados),
                _pesos(movimiento.neto_estimado),
                _pesos(movimiento.acumulado_estimado),
                estado,
            ]
        )

    componentes.tabla(
        [
            {"texto": "Mes"},
            {"texto": "Cobros", "alineacion": "der"},
            {"texto": "Pagos", "alineacion": "der"},
            {"texto": "Neto", "alineacion": "der"},
            {"texto": "Acumulado", "alineacion": "der"},
            {"texto": "Lectura"},
        ],
        filas,
    )


def render(db: BaseDatos, persona_id: int) -> None:
    st.title("Planificar")
    st.caption("Una mirada sencilla a los cobros y pagos que ya conocemos.")

    c1, c2 = st.columns(2)
    with c1:
        horizonte = st.selectbox(
            "¿Cuántos meses querés mirar?",
            options=[3, 6, 12, 24, 36],
            index=2,
            key="planificacion_horizonte",
        )
    with c2:
        fecha_corte = st.date_input(
            "Tomar como punto de partida",
            value=date.today(),
            key="planificacion_fecha_corte",
            help=(
                "Los movimientos anteriores o iguales a esta fecha "
                "quedan fuera del plan futuro."
            ),
        )

    try:
        plan = ServicioPlanificacionFinancieraPersona(db).obtener(
            persona_id,
            fecha_corte=fecha_corte,
            horizonte_meses=horizonte,
        )
    except ValueError as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    componentes.nota_contextual(
        (
            f"Plan desde {_fecha(fecha_corte)} hasta {_fecha(plan.fecha_fin)}. "
            "Solo usa compromisos futuros ya registrados en el sistema."
        ),
        "info",
    )

    _render_resumen(plan)
    _render_grafico(plan)
    _render_tabla(plan)

    with st.expander("Qué no está incluido"):
        st.markdown(
            """
Este plan **no** conoce tu sueldo, otros gastos, efectivo disponible,
ahorros externos, otras inversiones ni otras deudas que no estén registradas
acá.

Por eso sirve como mapa de los préstamos e inversiones administrados por esta
aplicación, no como presupuesto personal completo.
"""
        )

    with st.expander("Cómo leer esta pantalla"):
        st.markdown(
            """
**Cobros**: dinero que esperás recibir por inversiones registradas.

**Pagos**: dinero que esperás entregar por préstamos registrados.

**Neto del mes**: cobros menos pagos durante ese mes.

**Acumulado**: suma de los netos desde el comienzo del período.

**Reserva sugerida**: monto que, partiendo de cero, cubriría el peor déficit
acumulado de los movimientos que conocemos. No reemplaza un fondo de emergencia
ni contempla gastos externos.
"""
        )
