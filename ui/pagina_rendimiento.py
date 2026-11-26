"""Pantalla de rendimiento efectivo y costo por operación."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st

from aplicacion.consultas.resultados_operaciones_persona import (
    ResultadoOperacionPersona,
)
from infraestructura.composicion.analisis_financiero import (
    crear_servicio_resultados_operaciones_persona,
)
from . import componentes


def _pct(valor: Decimal | None) -> str:
    if valor is None:
        return "No disponible"
    return f"{valor * Decimal('100'):.2f}%"


def _pesos(valor: Decimal) -> str:
    negativo = valor < Decimal("0")
    entero, decimales = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{'-' if negativo else ''}$ {entero},{decimales}"


def _fecha(valor: date | None) -> str:
    return "—" if valor is None else valor.strftime("%d/%m/%Y")


def _render_resumen(disponibles: int, total: int) -> None:
    st.subheader("Resultados por operación")
    if total == 0:
        componentes.estado_vacio(
            "📊",
            "Todavía no hay operaciones identificables para analizar",
            "Cuando existan aportes, desembolsos o pagos reales vinculados a un préstamo, vas a poder consultar su rendimiento o costo.",
        )
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Con tasa calculable", disponibles)
    col2.metric("Operaciones analizadas", total)
    col3.metric("Sin conclusión todavía", total - disponibles)


def _render_tabla(operaciones: tuple[ResultadoOperacionPersona, ...]) -> None:
    filas = []
    for operacion in operaciones:
        estado = "Disponible" if operacion.evidencia_suficiente else "Pendiente de evidencia"
        tasa = (
            _pct(operacion.xirr_anual)
            if operacion.evidencia_suficiente
            else operacion.motivo_no_disponible or "Todavía no disponible"
        )
        filas.append(
            [
                operacion.prestamo_numero,
                "Inversión" if operacion.rol == "inversor" else "Deuda",
                operacion.metrica_nombre,
                tasa,
                _pct(operacion.rendimiento_real_anual),
                _pct(operacion.xirr_usd_anual),
                str(operacion.cantidad_flujos),
                estado,
            ]
        )

    componentes.tabla(
        [
            {"texto": "Préstamo"},
            {"texto": "Rol"},
            {"texto": "Indicador"},
            {"texto": "Tasa efectiva"},
            {"texto": "Resultado real"},
            {"texto": "Tasa USD"},
            {"texto": "Movimientos", "alineacion": "der"},
            {"texto": "Evidencia"},
        ],
        filas,
    )


def _render_detalle(operacion: ResultadoOperacionPersona) -> None:
    rol = "Inversión" if operacion.rol == "inversor" else "Deuda"
    st.subheader(f"{operacion.metrica_nombre} · {operacion.prestamo_numero}")
    st.caption(
        f"Rol: {rol}. Período: {_fecha(operacion.fecha_inicio)} a "
        f"{_fecha(operacion.fecha_fin)}. Los movimientos son exclusivos de esta operación."
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Tasa efectiva anual", _pct(operacion.xirr_anual))
    col2.metric("Resultado real anual", _pct(operacion.rendimiento_real_anual))
    col3.metric("Tasa efectiva USD", _pct(operacion.xirr_usd_anual))

    if not operacion.evidencia_suficiente:
        componentes.nota_contextual(
            (
                "Todavía no mostramos una tasa ARS porque los flujos reales de "
                "esta operación no alcanzan para sostener un cálculo único. "
                f"{operacion.motivo_no_disponible or ''}"
            ),
            "warning",
        )
    elif operacion.xirr_usd_anual is None:
        componentes.nota_contextual(
            "La tasa USD no está disponible porque al menos un movimiento real "
            "no tiene una conversión USD explícita o verificable.",
            "info",
        )

    filas = []
    for flujo in operacion.flujos_reales:
        if flujo.monto_ars > 0:
            sentido = "Entrada"
        elif flujo.monto_ars < 0:
            sentido = "Salida"
        else:
            sentido = "Neutro"
        filas.append(
            [
                _fecha(flujo.fecha),
                flujo.tipo,
                sentido,
                _pesos(flujo.monto_ars),
                "—" if flujo.monto_usd is None else f"USD {flujo.monto_usd:,.2f}",
                "Real",
            ]
        )

    componentes.tabla(
        [
            {"texto": "Fecha"},
            {"texto": "Movimiento"},
            {"texto": "Sentido"},
            {"texto": "ARS", "alineacion": "der"},
            {"texto": "USD", "alineacion": "der"},
            {"texto": "Naturaleza"},
        ],
        filas,
    )

    with st.expander("¿Cómo se calcula y qué significa?"):
        if operacion.rol == "inversor":
            st.markdown(
                """
**Rendimiento efectivo anual:** XIRR de los aportes y cobros reales de este
préstamo, usando las fechas registradas.

**Resultado real anual:** ajusta esa tasa por el supuesto de inflación mensual
elegido en esta pantalla. No modifica los movimientos registrados.

Una tasa no significa que el futuro vaya a repetir ese resultado.
"""
            )
        else:
            st.markdown(
                """
**Costo efectivo anual:** XIRR del desembolso recibido y los pagos reales de
este préstamo, desde el punto de vista del deudor.

**Costo real anual:** expresa ese costo después del supuesto de inflación
mensual elegido.

No es una proyección de cuotas futuras ni reemplaza las condiciones del acuerdo.
"""
            )


def render(db: object, persona_id: int) -> None:
    st.title("Rendimiento")
    st.caption(
        "Qué rendimiento o costo muestran los movimientos que realmente ocurrieron."
    )

    inflacion_pct = st.number_input(
        "Inflación mensual supuesta para el resultado real (%)",
        min_value=-99.0,
        max_value=100.0,
        value=5.0,
        step=0.5,
        format="%.2f",
        key="rendimiento_inflacion",
        help="Solo cambia la lectura en términos reales. No modifica préstamos, pagos ni contratos.",
    )
    fecha_corte = st.date_input(
        "Fecha de corte",
        value=date.today(),
        key="rendimiento_fecha_corte",
    )

    try:
        resultados = crear_servicio_resultados_operaciones_persona(db).obtener(
            persona_id,
            fecha_corte=fecha_corte,
            inflacion_mensual_supuesta=Decimal(str(inflacion_pct)) / Decimal("100"),
        )
    except ValueError as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    componentes.nota_contextual(
        (
            f"Cada tasa se calcula por separado para un préstamo y un rol, usando "
            f"movimientos reales hasta {_fecha(fecha_corte)}. No se mezclan préstamos "
            "distintos ni flujos futuros."
        ),
        "info",
    )

    _render_resumen(len(resultados.disponibles), len(resultados.operaciones))
    if resultados.operaciones:
        _render_tabla(resultados.operaciones)
        opciones = {
            indice: operacion
            for indice, operacion in enumerate(resultados.operaciones)
        }
        seleccion = st.selectbox(
            "Operación para ver la evidencia",
            options=list(opciones),
            format_func=lambda indice: (
                f"{opciones[indice].prestamo_numero} — "
                f"{opciones[indice].metrica_nombre}"
            ),
            key="rendimiento_operacion",
        )
        _render_detalle(opciones[seleccion])

    if resultados.advertencias:
        with st.expander("Observaciones del análisis"):
            for advertencia in resultados.advertencias:
                st.warning(advertencia)

    with st.expander("Importante antes de tomar una decisión"):
        st.markdown(
            """
Una tasa histórica no garantiza que el futuro vaya a repetir ese resultado.

Una tasa no disponible no significa que la inversión haya salido mal. Puede
significar que todavía no existen movimientos suficientes, que faltan
conversiones o que los flujos no permiten resolver una tasa única.

Las métricas no agregan ingresos, gastos, tipos de cambio ni movimientos que
el sistema no tenga registrados.
"""
        )
