"""Página humana de la aplicación.

No reemplaza las pantallas de administración. Es la vista que debería poder
usar una persona que solo quiere responder tres preguntas:

1. ¿Qué tengo?
2. ¿Qué viene después?
3. ¿Qué significa cada número?
"""

from __future__ import annotations

import html
from datetime import date, timedelta
from decimal import Decimal

import plotly.graph_objects as go
import streamlit as st

from aplicacion.consultas.posicion_financiera_persona import PosicionFinancieraPersona
from infraestructura.composicion.posicion_financiera import (
    crear_servicio_posicion_financiera_persona,
)
from infraestructura.composicion.analisis_financiero import (
    crear_servicio_cobros_futuros_persona,
)
from aplicacion.consultas.vista_humana_persona import ResumenHumanoPersona
from aplicacion.consultas.capacidad_pago_directa import (
    CobroFuturoDeclarado,
    EstadoCobroFuturo,
    FuenteCobroFuturo,
    evaluar_capacidad_pago_directa,
)
from infraestructura.composicion.vista_humana_persona import (
    crear_servicio_vista_humana_persona,
)

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



def _render_cobros_futuros_fechados(db: object, persona_id: int) -> None:
    """Muestra el calendario estimado sin agregarlo al margen declarado."""

    st.subheader("Próximos cobros de tus inversiones")
    st.caption(
        "Son cobros contractuales proyectados, todavía no recibidos. "
        "Podés probar qué pasaría si se demoran o no ingresan dentro del próximo año."
    )

    escenarios = {
        "Según la fecha prevista": 0,
        "Con 30 días de demora": 30,
        "Con 60 días de demora": 60,
        "Si no se cobran durante los próximos 12 meses": None,
    }
    escenario = st.selectbox(
        "Escenario de recepción",
        options=tuple(escenarios),
        key="mi_espacio_escenario_cobros_futuros",
    )
    demora_dias = escenarios[escenario]

    try:
        proyeccion = crear_servicio_cobros_futuros_persona(db).obtener(
            persona_id,
            horizonte_dias=365,
            demora_dias=demora_dias,
        )
    except ValueError as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    if not proyeccion.cobros:
        componentes.estado_vacio(
            "📅",
            "No hay cobros de inversiones proyectados para este período",
            "Cuando existan cuotas futuras a tu favor, aparecerán con su fecha estimada.",
        )
        return

    c1, c2 = st.columns(2)
    with c1:
        st.metric(
            "Total previsto originalmente",
            _pesos(proyeccion.total_previsto_ars),
        )
    with c2:
        st.metric(
            "Entraría dentro del escenario",
            _pesos(proyeccion.total_en_escenario_ars),
        )

    filas = []
    for cobro in proyeccion.cobros:
        if cobro.estado_escenario.value == "NO_RECIBIDO":
            fecha_escenario = "No ingresaría"
            estado = "No recibido en el período"
        elif cobro.estado_escenario.value == "FUERA_DEL_HORIZONTE":
            fecha_escenario = _fecha(cobro.fecha_escenario)
            estado = "Fuera de los próximos 12 meses"
        else:
            fecha_escenario = _fecha(cobro.fecha_escenario)
            estado = "Dentro del período"

        filas.append(
            [
                _fecha(cobro.fecha_prevista),
                fecha_escenario,
                cobro.prestamo_numero,
                _pesos(cobro.monto_ars),
                estado,
            ]
        )

    componentes.tabla(
        [
            {"texto": "Fecha prevista"},
            {"texto": "Fecha del escenario"},
            {"texto": "Préstamo"},
            {"texto": "Importe previsto (ARS)", "alineacion": "der"},
            {"texto": "Tratamiento"},
        ],
        filas,
    )

    if proyeccion.total_fuera_del_horizonte_ars > Decimal("0"):
        st.caption(
            f"Con esta demora, {_pesos(proyeccion.total_fuera_del_horizonte_ars)} "
            "quedarían fuera del horizonte de 12 meses."
        )
    if proyeccion.total_no_recibido_ars > Decimal("0"):
        componentes.nota_contextual(
            f"El escenario supone que no ingresarían {_pesos(proyeccion.total_no_recibido_ars)} "
            "durante los próximos 12 meses.",
            "warning",
        )

    st.caption(
        "Este calendario no confirma que esos pagos se realizarán. "
        "Tampoco se suma automáticamente al margen libre que declaraste: "
        "podrías haber incluido esos cobros al estimar cuánto te queda cada mes. "
        "Las demoras elegidas son hipótesis, no probabilidades calculadas. "
        "No uses una proyección como efectivo antes de recibirla."
    )

def _render_capacidad_pago_directa(db: object, persona_id: int) -> None:
    st.subheader("Evaluar una cuota nueva")
    st.caption(
        "Podés hacer esta comprobación sin registrar tu sueldo ni tus gastos. "
        "Además del margen habitual, podés probar cómo respondería tu ahorro "
        "si atravesaras uno o varios meses más ajustados."
    )

    with st.expander("¿Qué tengo que incluir en el dinero libre?"):
        st.markdown(
            """
Ingresá lo que suele quedarte después de pagar tus gastos habituales y las
cuotas/deudas que ya tenés: vivienda, servicios, comida, transporte, salud,
tarjetas y préstamos actuales.

**No incluyas la cuota nueva que estás evaluando.** Tampoco ingreses tu sueldo
ni el saldo total de tu cuenta.

Las obligaciones actuales ya están descontadas en el margen declarado; esta
cuenta no las vuelve a restar. El colchón es opcional y representa dinero que
querés conservar cada mes.
"""
        )

    col1, col2 = st.columns(2)
    with col1:
        margen = st.number_input(
            "Dinero libre mensual que calculás que te queda (ARS)",
            min_value=-1_000_000_000_000.0,
            max_value=1_000_000_000_000.0,
            value=0.0,
            step=10_000.0,
            format="%.2f",
            key="mi_espacio_margen_libre",
            help=(
                "Después de tus gastos normales y cuotas actuales; "
                "antes del nuevo compromiso. Podés ingresar cero o un valor negativo."
            ),
        )
    with col2:
        cuota = st.number_input(
            "Cuota mensual de la nueva propuesta (ARS)",
            min_value=0.0,
            max_value=1_000_000_000_000.0,
            value=0.0,
            step=10_000.0,
            format="%.2f",
            key="mi_espacio_cuota_nueva",
            help=(
                "Ingresá la cuota que te ofrecieron. Si cambia según el mes, "
                "usá la cuota más alta para esta primera comprobación."
            ),
        )

    colchon = st.number_input(
        "Dinero que querés conservar cada mes (opcional, ARS)",
        min_value=0.0,
        max_value=1_000_000_000_000.0,
        value=0.0,
        step=5_000.0,
        format="%.2f",
        key="mi_espacio_colchon_mensual",
        help=(
            "Se resta cada mes además de la nueva cuota. Es distinto del ahorro "
            "acumulado que podrías usar ante un imprevisto."
        ),
    )

    with st.expander("¿Tenés ahorros líquidos que podrían servirte de respaldo?"):
        st.caption(
            "Ingresá solo dinero al que podrías acceder hoy, por ejemplo efectivo "
            "o saldo bancario disponible. No incluyas el valor total de un vehículo, "
            "una propiedad, mercadería ni capital que todavía está prestado o invertido."
        )
        col3, col4 = st.columns(2)
        with col3:
            reserva = st.number_input(
                "Ahorro líquido disponible hoy (ARS)",
                min_value=0.0,
                max_value=1_000_000_000_000.0,
                value=0.0,
                step=10_000.0,
                format="%.2f",
                key="mi_espacio_reserva_liquida",
            )
        with col4:
            reserva_protegida = st.number_input(
                "Parte que preferís no tocar (ARS)",
                min_value=0.0,
                max_value=1_000_000_000_000.0,
                value=0.0,
                step=10_000.0,
                format="%.2f",
                key="mi_espacio_reserva_protegida",
                help=(
                    "Ese dinero queda fuera del respaldo utilizable. Por ejemplo, "
                    "si querés guardar una parte para salud o una emergencia mayor."
                ),
            )

    with st.expander("Probar un mes con menos dinero disponible"):
        evaluar_mes_ajustado = st.checkbox(
            "Quiero simular un período más difícil",
            key="mi_espacio_evaluar_mes_ajustado",
        )
        margen_ajustado = None
        meses_ajustados = 1
        if evaluar_mes_ajustado:
            margen_ajustado = st.number_input(
                "Dinero libre que estimás que te quedaría en ese mes (ARS)",
                min_value=-1_000_000_000_000.0,
                max_value=1_000_000_000_000.0,
                value=0.0,
                step=10_000.0,
                format="%.2f",
                key="mi_espacio_margen_mes_ajustado",
                help=(
                    "Después de tus gastos y obligaciones habituales, pero antes "
                    "de la cuota nueva. Puede ser cero o negativo."
                ),
            )
            meses_ajustados = int(
                st.number_input(
                    "¿Durante cuántos meses podría repetirse?",
                    min_value=1,
                    max_value=24,
                    value=1,
                    step=1,
                    key="mi_espacio_meses_ajustados",
                )
            )
            st.caption(
                "La simulación repite ese mismo margen durante la cantidad de meses "
                "indicada. Es un escenario hipotético, no una predicción."
            )

    with st.expander("¿Esperás recibir otros cobros que todavía no están en la aplicación?"):
        st.caption(
            "Podés agregar cobros externos con fecha prevista, por ejemplo una factura, "
            "un trabajo o una devolución. No repitas cobros de préstamos que ya aparecen "
            "en el calendario de tus inversiones. Tampoco agregues aquí dinero que ya "
            "recibiste: actualizá el ahorro líquido disponible hoy."
        )
        col_cobro_1, col_cobro_2 = st.columns(2)
        with col_cobro_1:
            importe_cobro = st.number_input(
                "Importe del cobro esperado (ARS)",
                min_value=0.0,
                max_value=1_000_000_000_000.0,
                value=0.0,
                step=10_000.0,
                format="%.2f",
                key="mi_espacio_cobro_importe",
            )
            fecha_cobro = st.date_input(
                "Fecha prevista de recepción",
                value=date.today() + timedelta(days=30),
                key="mi_espacio_cobro_fecha",
            )
        with col_cobro_2:
            origen_cobro = st.text_input(
                "¿De dónde vendría ese dinero?",
                key="mi_espacio_cobro_origen",
                max_chars=120,
                help="Por ejemplo: factura, trabajo pendiente, venta acordada o devolución.",
            )
            estado_cobro = st.selectbox(
                "Estado actual",
                options=(
                    EstadoCobroFuturo.PENDIENTE.value,
                    EstadoCobroFuturo.COBRADO.value,
                    EstadoCobroFuturo.CANCELADO.value,
                ),
                format_func=lambda estado: {
                    "PENDIENTE": "Todavía pendiente",
                    "COBRADO": "Ya lo recibí",
                    "CANCELADO": "Se canceló",
                }[estado],
                key="mi_espacio_cobro_estado",
            )
        cobro_incluido_margen = st.checkbox(
            "Ya tuve en cuenta este cobro al calcular mi dinero libre mensual",
            key="mi_espacio_cobro_incluido_margen",
            help=(
                "Así evitamos volver a sumarlo como respaldo. Si ya está incluido "
                "en el margen, se muestra pero no se agrega otra vez a la caja."
            ),
        )
        if st.button("Agregar cobro esperado", key="mi_espacio_agregar_cobro"):
            if importe_cobro <= 0 or not origen_cobro.strip():
                componentes.nota_contextual(
                    "Indicá un importe mayor que cero y el origen del cobro.",
                    "warning",
                )
            else:
                cobros_guardados = list(
                    st.session_state.get("mi_espacio_cobros_futuros_externos", [])
                )
                if len(cobros_guardados) >= 100:
                    componentes.nota_contextual(
                        "La simulación admite hasta 100 cobros externos.",
                        "warning",
                    )
                else:
                    cobros_guardados.append(
                        {
                            "importe": str(importe_cobro),
                            "fecha_prevista": fecha_cobro.isoformat(),
                            "origen": origen_cobro.strip(),
                            "estado": estado_cobro,
                            "incluido_en_margen": cobro_incluido_margen,
                        }
                    )
                    st.session_state["mi_espacio_cobros_futuros_externos"] = (
                        cobros_guardados
                    )
                    st.rerun()

        cobros_guardados = list(
            st.session_state.get("mi_espacio_cobros_futuros_externos", [])
        )
        if cobros_guardados:
            st.markdown("**Cobros externos cargados en esta sesión**")
            for indice, cobro_guardado in enumerate(cobros_guardados):
                fecha_guardada = date.fromisoformat(cobro_guardado["fecha_prevista"])
                estado_guardado = cobro_guardado["estado"]
                detalle_estado = {
                    "PENDIENTE": "Pendiente",
                    "COBRADO": "Ya recibido; no se suma como cobro futuro",
                    "CANCELADO": "Cancelado; no se suma",
                }[estado_guardado]
                st.write(
                    f"{cobro_guardado['origen']} · "
                    f"{_pesos(Decimal(cobro_guardado['importe']))} · "
                    f"{_fecha(fecha_guardada)} · {detalle_estado}"
                    + (
                        " · ya incluido en el margen"
                        if cobro_guardado["incluido_en_margen"]
                        else ""
                    )
                )
                if st.button(
                    "Quitar",
                    key=f"mi_espacio_quitar_cobro_{indice}",
                ):
                    cobros_guardados.pop(indice)
                    st.session_state["mi_espacio_cobros_futuros_externos"] = (
                        cobros_guardados
                    )
                    st.rerun()

    cobros_guardados = list(
        st.session_state.get("mi_espacio_cobros_futuros_externos", [])
    )
    cobros_externos_dominio = tuple(
        CobroFuturoDeclarado(
            importe=cobro["importe"],
            fecha_prevista=date.fromisoformat(cobro["fecha_prevista"]),
            origen=cobro["origen"],
            estado=cobro["estado"],
            incluido_en_margen=cobro["incluido_en_margen"],
        )
        for cobro in cobros_guardados
    )
    cobros_sistema_dominio: tuple[CobroFuturoDeclarado, ...] = ()
    proyeccion_sistema = None
    incluir_sistema_en_margen = False
    fecha_primer_vencimiento = None
    demora_cobros_dias = 0

    if evaluar_mes_ajustado:
        try:
            proyeccion_sistema = crear_servicio_cobros_futuros_persona(db).obtener(
                persona_id,
                fecha_corte=date.today(),
                horizonte_dias=1095,
                demora_dias=0,
            )
        except ValueError as exc:
            componentes.nota_contextual(
                f"No se pudieron leer los cobros contractuales del sistema: {exc}",
                "warning",
            )
            proyeccion_sistema = None

        cobros_sistema = (
            proyeccion_sistema.cobros if proyeccion_sistema is not None else ()
        )
        if cobros_sistema:
            with st.expander(
                "Cobros futuros de préstamos e inversiones registrados en la aplicación"
            ):
                st.metric(
                    "Total contractual proyectado (no recibido)",
                    _pesos(proyeccion_sistema.total_previsto_ars),
                )
                incluir_sistema_en_margen = st.checkbox(
                    "Ya consideré estos cobros del sistema al calcular mi margen libre",
                    key="mi_espacio_cobros_sistema_incluidos_margen",
                    help=(
                        "Si activás esta opción, los cobros contractuales siguen visibles, "
                        "pero no se vuelven a sumar al respaldo temporal."
                    ),
                )
                st.caption(
                    "Se leen del calendario contractual existente. Son proyecciones, "
                    "no pagos recibidos ni garantías de cobro."
                )
            cobros_sistema_dominio = tuple(
                CobroFuturoDeclarado(
                    importe=cobro.monto_ars,
                    fecha_prevista=cobro.fecha_prevista,
                    origen=f"Préstamo {cobro.prestamo_numero}",
                    incluido_en_margen=incluir_sistema_en_margen,
                    fuente=FuenteCobroFuturo.SISTEMA_CONTRACTUAL,
                    referencia=(
                        f"{cobro.prestamo_id}:"
                        f"{cobro.fecha_prevista.isoformat()}:"
                        f"{cobro.tipo}"
                    ),
                )
                for cobro in cobros_sistema
            )

        if cobros_externos_dominio or cobros_sistema_dominio:
            st.markdown("**Fecha de vencimiento y recepción de todos los cobros**")
            fecha_primer_vencimiento = st.date_input(
                "Fecha del primer vencimiento que querés analizar",
                value=date.today() + timedelta(days=30),
                min_value=date.today(),
                key="mi_espacio_fecha_primer_vencimiento",
            )
            escenario_cobros = st.selectbox(
                "¿Cuándo suponés que llegarían los cobros pendientes?",
                options=(0, 30, 60, None),
                format_func=lambda dias: {
                    0: "En la fecha prevista",
                    30: "Con 30 días de demora",
                    60: "Con 60 días de demora",
                    None: "No se reciben durante el período",
                }[dias],
                key="mi_espacio_demora_cobros_externos",
            )
            demora_cobros_dias = escenario_cobros

    cobros_futuros_dominio = cobros_externos_dominio + cobros_sistema_dominio

    valores_actuales = (
        str(margen),
        str(cuota),
        str(colchon),
        str(reserva),
        str(reserva_protegida),
        str(margen_ajustado) if margen_ajustado is not None else None,
        meses_ajustados if margen_ajustado is not None else None,
        tuple(
            (
                cobro["importe"],
                cobro["fecha_prevista"],
                cobro["origen"],
                cobro["estado"],
                cobro["incluido_en_margen"],
            )
            for cobro in cobros_guardados
        ),
        tuple(
            (
                cobro.referencia,
                cobro.fecha_prevista.isoformat(),
                str(cobro.importe),
                cobro.incluido_en_margen,
            )
            for cobro in cobros_sistema_dominio
        ),
        incluir_sistema_en_margen,
        fecha_primer_vencimiento.isoformat()
        if fecha_primer_vencimiento is not None
        else None,
        demora_cobros_dias,
    )
    if st.button(
        "Calcular cuánto quedaría",
        key="mi_espacio_calcular_capacidad",
        type="primary",
    ):
        try:
            resultado = evaluar_capacidad_pago_directa(
                margen_libre_mensual=Decimal(str(margen)),
                cuota_nueva_mensual=Decimal(str(cuota)),
                colchon_mensual=Decimal(str(colchon)),
                reserva_liquida_disponible=Decimal(str(reserva)),
                reserva_minima_protegida=Decimal(str(reserva_protegida)),
                margen_libre_mes_ajustado=(
                    Decimal(str(margen_ajustado))
                    if margen_ajustado is not None
                    else None
                ),
                meses_escenario_ajustado=meses_ajustados,
                cobros_futuros=cobros_futuros_dominio,
                fecha_primer_vencimiento=fecha_primer_vencimiento,
                demora_cobros_dias=demora_cobros_dias,
                fecha_referencia=date.today(),
            )
        except ValueError as exc:
            st.session_state.pop("mi_espacio_capacidad_resultado", None)
            st.session_state.pop("mi_espacio_capacidad_entrada", None)
            componentes.nota_contextual(str(exc), "error")
            return

        st.session_state["mi_espacio_capacidad_resultado"] = resultado
        st.session_state["mi_espacio_capacidad_entrada"] = valores_actuales

    resultado = st.session_state.get("mi_espacio_capacidad_resultado")
    entrada_guardada = st.session_state.get("mi_espacio_capacidad_entrada")
    if resultado is not None and entrada_guardada == valores_actuales:
        st.divider()
        st.metric(
            "Dinero estimado después de la cuota",
            _pesos(resultado.remanente_mensual),
        )
        if resultado.porcentaje_margen_comprometido is not None:
            st.metric(
                "Parte del margen libre que usaría la cuota",
                f"{resultado.porcentaje_margen_comprometido:.2f}%",
            )

        if resultado.remanente_mensual < Decimal("0"):
            componentes.nota_contextual(
                f"Con estos importes faltarían {_pesos(abs(resultado.remanente_mensual))} por mes, "
                "antes de considerar otros imprevistos.",
                "warning",
            )
        elif resultado.remanente_mensual == Decimal("0"):
            componentes.nota_contextual(
                "La cuota y el colchón consumirían todo el margen declarado. "
                "No quedaría dinero libre adicional.",
                "warning",
            )
        else:
            componentes.nota_contextual(
                f"Con los valores ingresados quedarían {_pesos(resultado.remanente_mensual)} "
                "por mes después de la nueva cuota y el colchón elegido. "
                "Es una estimación, no una garantía de que el compromiso sea sostenible.",
                "info",
            )

        if resultado.margen_libre_declarado < Decimal("0"):
            componentes.nota_contextual(
                "El margen que ingresaste ya es negativo antes de sumar la cuota nueva.",
                "warning",
            )

        respaldo = resultado.respaldo_liquidez
        if (
            respaldo.reserva_liquida_declarada > Decimal("0")
            or respaldo.reserva_minima_protegida > Decimal("0")
        ):
            st.metric(
                "Respaldo líquido que podrías usar",
                _pesos(respaldo.reserva_utilizable),
            )
            st.caption(
                f"De {_pesos(respaldo.reserva_liquida_declarada)} disponibles, "
                f"dejás {_pesos(respaldo.reserva_minima_protegida)} protegidos. "
                "El resto se mantiene separado del margen mensual."
            )

        if respaldo.margen_libre_mes_ajustado is not None:
            st.markdown("**Resultado del mes más ajustado**")
            st.metric(
                "Dinero que quedaría en ese mes después de la cuota",
                _pesos(respaldo.remanente_mes_ajustado),
            )
            if respaldo.faltante_mensual_escenario == Decimal("0.00"):
                componentes.nota_contextual(
                    "En este escenario, el margen del mes alcanzaría para la cuota "
                    "y el colchón. No necesitarías usar el ahorro de respaldo.",
                    "success",
                )
            else:
                meses = respaldo.meses_escenario_ajustado
                cubiertos = respaldo.meses_completos_cubiertos
                faltante = respaldo.faltante_mensual_escenario
                if respaldo.faltante_no_cubierto_escenario == Decimal("0.00"):
                    componentes.nota_contextual(
                        f"El faltante sería de {_pesos(faltante)} por mes. "
                        f"Tu respaldo cubriría los {meses} mes(es) del escenario "
                        f"y quedarían {_pesos(respaldo.respaldo_restante_escenario)} "
                        "de reserva utilizable.",
                        "info",
                    )
                else:
                    componentes.nota_contextual(
                        f"El faltante sería de {_pesos(faltante)} por mes. "
                        f"El respaldo cubriría {cubiertos} de {meses} mes(es) completos. "
                        f"Para cubrir todo el escenario todavía faltarían "
                        f"{_pesos(respaldo.faltante_no_cubierto_escenario)}.",
                        "warning",
                    )

        proyeccion = respaldo.proyeccion_temporal
        if proyeccion is not None:
            st.markdown("**Respaldo con cobros por fecha: sistema y externos**")
            metricas_cobros = st.columns(4)
            with metricas_cobros[0]:
                st.metric(
                    "Cobros contractuales del sistema",
                    _pesos(proyeccion.total_cobros_sistema_en_escenario),
                )
            with metricas_cobros[1]:
                st.metric(
                    "Cobros externos declarados",
                    _pesos(proyeccion.total_cobros_externos_en_escenario),
                )
            with metricas_cobros[2]:
                st.metric(
                    "Respaldo al final del período",
                    _pesos(proyeccion.saldo_respaldo_final),
                )
            with metricas_cobros[3]:
                st.metric(
                    "Faltante que no llega a cubrirse",
                    _pesos(proyeccion.faltante_no_cubierto_total),
                )
            st.caption(
                f"Meses con faltante: {proyeccion.meses_con_faltante}. "
                "El origen de cada importe se conserva; el total de sistema es "
                "contractual proyectado y el externo es declarado por vos."
            )

            filas_cobros = [
                [
                    _fecha(periodo.fecha_vencimiento),
                    _pesos(periodo.cobros_sistema_hasta_vencimiento),
                    _pesos(periodo.cobros_externos_hasta_vencimiento),
                    _pesos(periodo.faltante_no_cubierto),
                    _pesos(periodo.respaldo_al_cierre),
                ]
                for periodo in proyeccion.periodos
            ]
            componentes.tabla(
                [
                    {"texto": "Vencimiento"},
                    {"texto": "Cobros del sistema", "alineacion": "der"},
                    {"texto": "Cobros externos", "alineacion": "der"},
                    {"texto": "Faltante sin cubrir", "alineacion": "der"},
                    {"texto": "Respaldo restante", "alineacion": "der"},
                ],
                filas_cobros,
            )
            if proyeccion.total_cobros_fuera_horizonte > Decimal("0"):
                st.caption(
                    "Cobros que llegarían después del último vencimiento del escenario: "
                    f"{_pesos(proyeccion.total_cobros_fuera_horizonte)}. "
                    "No se usan para cubrir meses anteriores."
                )
            if proyeccion.total_cobros_vencidos_no_recibidos > Decimal("0"):
                st.caption(
                    "Cobros con fecha pasada que siguen pendientes y se excluyen: "
                    f"{_pesos(proyeccion.total_cobros_vencidos_no_recibidos)}."
                )
            if proyeccion.total_cobros_no_recibidos_escenario > Decimal("0"):
                st.caption(
                    "Cobros que el escenario supone no recibir durante el período: "
                    f"{_pesos(proyeccion.total_cobros_no_recibidos_escenario)}."
                )
            if proyeccion.total_cobros_incluidos_en_margen_excluidos > Decimal("0"):
                st.caption(
                    "Cobros que ya habías incluido en el margen y no se vuelven a sumar: "
                    f"{_pesos(proyeccion.total_cobros_incluidos_en_margen_excluidos)}."
                )
            if (
                proyeccion.total_cobros_ya_recibidos_excluidos > Decimal("0")
                or proyeccion.total_cobros_cancelados_excluidos > Decimal("0")
            ):
                st.caption(
                    "Los cobros ya recibidos o cancelados se excluyen de la proyección. "
                    "Si ya recibiste el dinero y sigue disponible, actualizá el ahorro "
                    "líquido declarado para reflejarlo una sola vez."
                )
            st.caption(
                "Cada cobro pendiente se incorpora recién en su fecha prevista o demorada. "
                "No cubre vencimientos anteriores. Es una hipótesis declarada: no estima "
                "probabilidades ni garantiza que el pago se concrete."
            )
        elif cobros_futuros_dominio:
            st.caption(
                "Los cobros externos están cargados, pero para probar su efecto sobre "
                "el respaldo activá también el escenario de margen ajustado."
            )
        else:
            st.caption(
                "Los cobros que esperás recibir no se suman al ahorro disponible hoy: "
                "se deben analizar por su fecha y pueden demorarse o no concretarse."
            )
    elif resultado is not None:
        st.caption("Cambiaste uno o más valores. Volvé a calcular para actualizar el resultado.")

    st.caption(
        "Estimación declarada por vos; no verifica ingresos, ahorros ni gastos. "
        "Se conserva únicamente en esta sesión y no se guarda en la base de datos. "
        "No es una relación deuda/ingresos ni una aprobación crediticia."
    )


def render(db: object, persona_id: int) -> None:
    componentes.renderizar_nota_pendiente()

    try:
        resumen = crear_servicio_vista_humana_persona(db).obtener(persona_id)
    except ValueError as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    st.title("Mi espacio")
    st.caption("Tu situación financiera, explicada de manera simple.")

    componentes.render_html(
        f'<div class="saludo">Hola, {html.escape(resumen.nombre)} 👋</div>'
    )
    st.write(_intro(resumen))

    posicion = crear_servicio_posicion_financiera_persona(db).obtener(persona_id)
    _render_posicion_financiera(posicion)

    _render_resumen(resumen)

    if "INVERSOR" in _roles(resumen):
        _render_cobros_futuros_fechados(db, persona_id)

    _render_capacidad_pago_directa(db, persona_id)

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
