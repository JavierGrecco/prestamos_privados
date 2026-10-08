"""Página humana de la aplicación.

No reemplaza las pantallas de administración. Es la vista que debería poder
usar una persona que solo quiere responder tres preguntas:

1. ¿Qué tengo?
2. ¿Qué viene después?
3. ¿Qué significa cada número?
"""

from __future__ import annotations

import html
from decimal import Decimal

import plotly.graph_objects as go
import streamlit as st

from aplicacion.consultas.posicion_financiera_persona import (
    PosicionFinancieraPersona,
    ServicioPosicionFinancieraPersona,
)
from aplicacion.consultas.vista_humana_persona import (
    ResumenHumanoPersona,
    ServicioVistaHumanaPersona,
)
from infraestructura.db import BaseDatos

from . import componentes


def _pesos(valor: Decimal | None) -> str:
    if valor is None:
        return "—"
    negativo = valor < 0
    entero, decimales = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{'-' if negativo else ''}$ {entero},{decimales}"


def _fecha(fecha) -> str:
    return fecha.strftime("%d/%m/%Y") if fecha else "—"


def _roles(resumen: ResumenHumanoPersona) -> set[str]:
    return set(resumen.roles)


def _navegar_detalle(prestamo_id: int) -> None:
    st.session_state["prestamo_seleccionado"] = prestamo_id
    st.session_state["pagina_pendiente"] = "detalle_financiero"
    st.rerun()


def _intro(resumen: ResumenHumanoPersona) -> str:
    tiene_deuda = any(p.rol == "DEUDOR" for p in resumen.posiciones)
    tiene_inversion = any(p.rol == "INVERSOR" for p in resumen.posiciones)

    if tiene_deuda and tiene_inversion:
        return (
            "Acá ves, en un solo lugar, tus inversiones, tus préstamos "
            "y qué movimiento importante viene después."
        )
    if tiene_deuda:
        return (
            "Acá ves qué pagos tenés pendientes y qué viene después, "
            "sin necesidad de conocer términos financieros."
        )
    if tiene_inversion:
        return (
            "Acá ves cuánto invertiste, cuánto ya cobraste "
            "y qué cobros están previstos."
        )
    return "Acá podés consultar tu situación financiera de forma simple y clara."



def _render_posicion_financiera(posicion: PosicionFinancieraPersona) -> None:
    st.subheader("Tu posición financiera")
    st.caption(
        "Esto resume únicamente préstamos e inversiones registrados en la aplicación. "
        "No representa todo tu patrimonio ni incluye dinero o bienes que no estén registrados acá."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Capital invertido", _pesos(posicion.capital_invertido))
    with c2:
        st.metric(
            "Capital pendiente de deuda",
            _pesos(posicion.capital_deuda_pendiente),
        )
    with c3:
        st.metric(
            "Posición neta de capital",
            _pesos(posicion.posicion_neta_capital),
        )

    if posicion.posicion_neta_es_positiva:
        componentes.nota_contextual(
            (
                "En los préstamos registrados, hoy tenés más capital invertido "
                "que capital pendiente de deuda."
            ),
            "success",
        )
    else:
        componentes.nota_contextual(
            (
                "En los préstamos registrados, hoy tenés más capital pendiente "
                "de deuda que capital invertido."
            ),
            "warning",
        )

    with st.expander("¿Cómo se obtiene esta posición?"):
        st.markdown(
            f"""
**Capital invertido**: {_pesos(posicion.capital_invertido)}.  
Es el capital de tus inversiones activas registradas.

**Capital pendiente de deuda**: {_pesos(posicion.capital_deuda_pendiente)}.  
Es el capital que todavía figura pendiente en tus préstamos activos.

**Posición neta de capital**: {_pesos(posicion.posicion_neta_capital)}.  
Se obtiene restando el capital pendiente de deuda al capital invertido.

> Este cálculo sirve para entender tu exposición dentro de esta aplicación.
> No es una valuación de tu patrimonio total.
"""
        )

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Cobros reales registrados", _pesos(posicion.cobros_reales))
    with c2:
        st.metric("Pagos reales registrados", _pesos(posicion.pagos_reales))

    c1, c2 = st.columns(2)
    with c1:
        st.metric(
            "Cobros futuros estimados",
            _pesos(posicion.cobros_futuros_estimados),
        )
    with c2:
        st.metric(
            "Pagos futuros estimados",
            _pesos(posicion.pagos_futuros_estimados),
        )

    componentes.nota_contextual(
        (
            f"Movimiento neto futuro estimado: "
            f"{_pesos(posicion.flujo_neto_futuro_estimado)}. "
            "Es una proyección de cobros menos pagos futuros, no un saldo disponible."
        ),
        "info",
    )

    st.caption(
        "Los movimientos históricos de abajo son reales y están agrupados por mes."
    )
    st.caption("La evolución muestra el movimiento acumulado de caja registrado; no es patrimonio.")
    _render_evolucion_real(posicion)


def _render_evolucion_real(posicion: PosicionFinancieraPersona) -> None:
    if not posicion.movimientos_mensuales or not any(
        m.entradas > Decimal("0") or m.salidas > Decimal("0")
        for m in posicion.movimientos_mensuales
    ):
        componentes.estado_vacio(
            "📊",
            "Todavía no hay movimientos para graficar",
            "Cuando existan cobros, pagos o aportes, vas a poder ver su evolución mensual.",
        )
        return

    etiquetas = [
        movimiento.periodo.strftime("%m/%Y")
        for movimiento in posicion.movimientos_mensuales
    ]
    acumulados = [
        float(movimiento.acumulado)
        for movimiento in posicion.movimientos_mensuales
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=etiquetas,
            y=acumulados,
            mode="lines+markers",
            name="Movimiento acumulado",
        )
    )
    fig.update_layout(
        title="Evolución de movimientos reales acumulados",
        xaxis_title="Mes",
        yaxis_title="ARS acumulados",
        margin=dict(l=10, r=10, t=50, b=10),
        height=320,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    filas = []
    for movimiento in reversed(posicion.movimientos_mensuales):
        filas.append(
            [
                movimiento.periodo.strftime("%m/%Y"),
                _pesos(movimiento.entradas),
                _pesos(movimiento.salidas),
                _pesos(movimiento.neto),
                _pesos(movimiento.acumulado),
            ]
        )

    componentes.tabla(
        [
            {"texto": "Mes"},
            {"texto": "Entradas", "alineacion": "der"},
            {"texto": "Salidas", "alineacion": "der"},
            {"texto": "Neto", "alineacion": "der"},
            {"texto": "Acumulado", "alineacion": "der"},
        ],
        filas,
    )

def _render_resumen(resumen: ResumenHumanoPersona) -> None:
    roles = _roles(resumen)
    metricas: list[tuple[str, str]] = []

    if "INVERSOR" in roles and resumen.capital_invertido > Decimal("0"):
        metricas.append(("Tenés invertido", _pesos(resumen.capital_invertido)))
    if "DEUDOR" in roles and resumen.total_pagos_deuda_estimados > Decimal("0"):
        metricas.append(("Pagos pendientes estimados", _pesos(resumen.total_pagos_deuda_estimados)))
    if resumen.proximo_cobro and "INVERSOR" in roles:
        _, monto = resumen.proximo_cobro
        metricas.append(("Próximo cobro estimado", _pesos(monto)))
    if resumen.proximo_pago and "DEUDOR" in roles:
        _, monto = resumen.proximo_pago
        metricas.append(("Próximo pago estimado", _pesos(monto)))

    if metricas:
        cols = st.columns(len(metricas))
        for col, (titulo, valor) in zip(cols, metricas):
            with col:
                st.metric(titulo, valor)

    if resumen.proximo_cobro and "INVERSOR" in roles:
        fecha, _ = resumen.proximo_cobro
        componentes.nota_contextual(
            (
                f"Tu próximo cobro estimado es el {_fecha(fecha)}. "
                "Es una proyección contractual, no una promesa de cobro."
            ),
            "info",
        )

    if resumen.proximo_pago and "DEUDOR" in roles:
        fecha, _ = resumen.proximo_pago
        componentes.nota_contextual(
            (
                f"Tu próximo pago estimado vence el {_fecha(fecha)}. "
                "El monto mostrado puede cambiar si existe un hecho nuevo."
            ),
            "info",
        )


def _render_posicion(posicion) -> None:
    destino = html.escape(posicion.destino or "Sin destino indicado")
    icono = "📈" if posicion.rol == "INVERSOR" else "🧾"

    componentes.render_html(
        f"""
        <div class="bloque-impacto">
            <div class="bloque-impacto-icono">{icono}</div>
            <div class="bloque-impacto-cuerpo">
                <div class="bloque-impacto-veredicto">
                    {html.escape(posicion.rol_humano)} · {html.escape(posicion.estado_humano)}
                </div>
                <div style="font-size:1.2rem;font-weight:700;">
                    {html.escape(posicion.prestamo_numero)}
                </div>
                <div class="detalle-item-sub">{destino}</div>
            </div>
        </div>
        """
    )

    c1, c2 = st.columns(2)

    if posicion.rol == "DEUDOR":
        with c1:
            st.metric("Capital pendiente", _pesos(posicion.capital_pendiente))
        with c2:
            if posicion.proximo_monto and posicion.proxima_fecha:
                st.metric(
                    "Próximo pago estimado",
                    _pesos(posicion.proximo_monto),
                )
                st.caption(f"Vence el {_fecha(posicion.proxima_fecha)}")
            else:
                st.metric("Próximo pago", "No hay uno proyectado")

        if posicion.cuotas_totales:
            cerradas = posicion.cuotas_cerradas or 0
            st.caption(
                f"Cuotas pagadas: {cerradas} de {posicion.cuotas_totales}"
            )

    else:
        with c1:
            st.metric("Invertiste", _pesos(posicion.monto_principal))
        with c2:
            st.metric("Cobrado hasta hoy", _pesos(posicion.cobrado_real))

        if posicion.proximo_monto and posicion.proxima_fecha:
            st.info(
                f"Próximo cobro estimado: {_pesos(posicion.proximo_monto)} "
                f"el {_fecha(posicion.proxima_fecha)}."
            )

        if posicion.porcentaje_inversor is not None:
            st.caption(
                "Tu participación en este préstamo: "
                f"{posicion.porcentaje_inversor * Decimal('100'):.2f}%."
            )

    if posicion.advertencia:
        st.warning(posicion.advertencia)

    if st.button(
        "Ver detalle financiero",
        key=f"mi_espacio_detalle_{posicion.prestamo_id}_{posicion.rol.lower()}",
        use_container_width=True,
    ):
        _navegar_detalle(posicion.prestamo_id)


def _render_actividad(resumen: ResumenHumanoPersona) -> None:
    if not resumen.actividad_reciente:
        componentes.estado_vacio(
            "🕊️",
            "Todavía no hay movimientos registrados",
            "Cuando exista un pago, cobro o aporte, va a aparecer acá.",
        )
        return

    filas = []
    for item in resumen.actividad_reciente:
        filas.append(
            [
                _fecha(item.fecha),
                item.texto,
                item.prestamo_numero,
                _pesos(item.monto),
            ]
        )

    componentes.tabla(
        [
            {"texto": "Fecha"},
            {"texto": "Qué pasó"},
            {"texto": "Préstamo"},
            {"texto": "Monto", "alineacion": "der"},
        ],
        filas,
    )


def _render_glosario() -> None:
    with st.expander("Entender estos números"):
        st.markdown(
            """
**Capital**  
Es el dinero original del préstamo. No incluye por sí solo los intereses.

**Cuota**  
Es el importe que corresponde pagar en una fecha determinada.

**Interés**  
Es el costo por usar dinero prestado. En una inversión, forma parte de lo que genera el cobro.

**Mora**  
Es un importe adicional que puede aparecer cuando un pago se realiza después de su vencimiento, según las reglas del préstamo.

**Adelanto**  
Es pagar antes de tiempo una parte del capital. Puede usarse para bajar cuotas o terminar antes, según las condiciones.

**Estimado**  
Significa que todavía no ocurrió. Se muestra para ayudarte a planificar y no debe interpretarse como una garantía.

**Participación**  
Es el porcentaje del préstamo que corresponde a tu inversión.
"""
        )


def render(db: BaseDatos, persona_id: int) -> None:
    componentes.renderizar_nota_pendiente()

    try:
        resumen = ServicioVistaHumanaPersona(db).obtener(persona_id)
    except ValueError as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    st.title("Mi espacio")
    st.caption("Tu situación financiera, explicada de manera simple.")

    componentes.render_html(
        f'<div class="saludo">Hola, {html.escape(resumen.nombre)} 👋</div>'
    )
    st.write(_intro(resumen))

    posicion = ServicioPosicionFinancieraPersona(db).obtener(persona_id)
    _render_posicion_financiera(posicion)

    _render_resumen(resumen)

    posiciones_inversion = [
        p for p in resumen.posiciones if p.rol == "INVERSOR"
    ]
    posiciones_deuda = [
        p for p in resumen.posiciones if p.rol == "DEUDOR"
    ]

    if posiciones_inversion:
        st.subheader("Tus inversiones")
        st.caption(
            "El monto invertido es real y confirmado. "
            "Los cobros futuros aparecen como estimados."
        )
        for posicion in posiciones_inversion:
            _render_posicion(posicion)

    if posiciones_deuda:
        st.subheader("Tus préstamos")
        st.caption(
            "El capital pendiente surge del estado actual del préstamo. "
            "Los próximos pagos son estimaciones contractuales."
        )
        for posicion in posiciones_deuda:
            _render_posicion(posicion)

    st.subheader("Actividad reciente")
    _render_actividad(resumen)

    if resumen.advertencias:
        with st.expander("Hay algo para mirar"):
            for advertencia in resumen.advertencias:
                st.warning(advertencia)

    _render_glosario()
