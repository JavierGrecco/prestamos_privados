"""Pantalla humana de rendimiento y costo efectivo por operación.

Las tasas se muestran solamente cuando los movimientos reales permiten
calcularlas. El resto queda explícitamente como no disponible.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st

from aplicacion.consultas.resultados_operaciones_persona import (
    ResultadoOperacionPersona,
    ServicioResultadosOperacionesPersona,
)
from infraestructura.db import BaseDatos

from . import componentes


def _pesos(valor: Decimal) -> str:
    negativo = valor < Decimal("0")
    entero, decimales = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{'-' if negativo else ''}$ {entero},{decimales}"


def _pct(valor: Decimal | None) -> str:
    if valor is None:
        return "Todavía no disponible"
    return f"{valor * Decimal('100'):.2f}%"


def _fecha(valor: date | None) -> str:
    return "—" if valor is None else valor.strftime("%d/%m/%Y")


def _render_resumen(
    disponibles: int,
    total: int,
) -> None:
    st.subheader("Resultados de tus operaciones")
    if total == 0:
        componentes.estado_vacio(
            "📊",
            "Todavía no hay operaciones para analizar",
            "Cuando existan movimientos reales, vas a poder ver el resultado de cada operación.",
        )
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Operaciones con tasa calculable", disponibles)
    with c2:
        st.metric("Operaciones analizadas", total)
    with c3:
        st.metric("Sin conclusión todavía", total - disponibles)


def _render_tabla(
    operaciones: tuple[ResultadoOperacionPersona, ...],
) -> None:
    filas = []
    for op in operaciones:
        estado = "Disponible" if op.evidencia_suficiente else "Todavía no"
        resultado = (
            _pct(op.xirr_anual)
            if op.evidencia_suficiente
            else op.motivo_no_disponible or "Todavía no disponible"
        )
        filas.append(
            [
                f"{op.prestamo_numero} — {op.destino}",
                "Inversión" if op.rol == "inversor" else "Deuda",
                op.metrica_nombre,
                resultado,
                _pct(op.rendimiento_real_anual),
                _pct(op.xirr_usd_anual),
                str(op.cantidad_flujos),
                estado,
            ]
        )

    componentes.tabla(
        [
            {"texto": "Operación"},
            {"texto": "Rol"},
            {"texto": "Lectura"},
            {"texto": "Tasa efectiva"},
            {"texto": "Resultado real"},
            {"texto": "Tasa USD"},
            {"texto": "Movimientos", "alineacion": "der"},
            {"texto": "Estado"},
        ],
        filas,
    )


def _render_detalle(op: ResultadoOperacionPersona) -> None:
    st.subheader(f"{op.metrica_nombre}: {op.prestamo_numero}")
    st.caption(
        f"Destino: {op.destino}. Primer movimiento real: {_fecha(op.fecha_inicio)}."
    )

    if op.evidencia_suficiente:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Tasa efectiva anual", _pct(op.xirr_anual))
        with c2:
            st.metric("Resultado real anual", _pct(op.rendimiento_real_anual))
        with c3:
            st.metric("Tasa efectiva USD", _pct(op.xirr_usd_anual))
    else:
        componentes.nota_contextual(
            (
                "Todavía no mostramos una tasa porque los movimientos reales "
                "registrados no alcanzan para sostener un cálculo confiable. "
                f"{op.motivo_no_disponible or ''}"
            ),
            "warning",
        )

    filas = []
    for flujo in op.flujos_reales:
        filas.append(
            [
                _fecha(flujo.fecha),
                flujo.tipo,
                "Entrada" if flujo.monto_ars > 0 else "Salida",
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

    with st.expander("¿Cómo leer esta tasa?"):
        if op.rol == "inversor":
            st.markdown(
                """
**Tasa efectiva anual**: resume los movimientos reales de esta inversión
teniendo en cuenta sus fechas.

**Resultado real anual**: toma esa tasa y la compara con la inflación mensual
que elegiste arriba.

Una tasa no significa que el futuro vaya a repetir ese resultado. Se calcula
solamente con hechos ya registrados.
"""
            )
        else:
            st.markdown(
                """
**Costo efectivo anual**: resume cuánto te costó esta deuda considerando el
dinero que recibiste y los pagos reales, teniendo en cuenta sus fechas.

**Costo real anual**: compara ese costo con la inflación mensual elegida.

No es una predicción de lo que vas a pagar en el futuro.
"""
            )

    if op.xirr_usd_anual is None:
        st.caption(
            "La tasa USD solo se muestra cuando todos los movimientos reales "
            "de esta operación tienen una conversión USD disponible."
        )


def render(db: BaseDatos, persona_id: int) -> None:
    st.title("Rendimiento")
    st.caption(
        "Mirá el resultado real de tus operaciones. Las tasas se calculan solo "
        "cuando hay movimientos suficientes."
    )

    inflacion_pct = st.number_input(
        "Inflación mensual supuesta (%)",
        min_value=-99.0,
        max_value=100.0,
        value=5.0,
        step=0.5,
        format="%.2f",
        key="rendimiento_inflacion",
        help="Se usa únicamente para expresar el resultado real. No modifica ninguna operación.",
    )
    fecha_corte = st.date_input(
        "Fecha de corte",
        value=date.today(),
        key="rendimiento_fecha_corte",
    )

    try:
        resultados = ServicioResultadosOperacionesPersona(db).obtener(
            persona_id,
            fecha_corte=fecha_corte,
            inflacion_mensual_supuesta=Decimal(str(inflacion_pct)) / Decimal("100"),
        )
    except ValueError as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    componentes.nota_contextual(
        (
            "La tasa efectiva se basa en movimientos reales ya registrados. "
            "No es una promesa ni una proyección."
        ),
        "info",
    )

    _render_resumen(
        len(resultados.disponibles),
        len(resultados.operaciones),
    )
    if not resultados.operaciones:
        return

    _render_tabla(resultados.operaciones)

    nombres = [
        f"{op.prestamo_numero} — {op.metrica_nombre} — {op.destino}"
        for op in resultados.operaciones
    ]
    idx = st.selectbox(
        "Operación para ver en detalle",
        options=list(range(len(resultados.operaciones))),
        format_func=lambda i: nombres[i],
        key="rendimiento_operacion",
    )

    _render_detalle(resultados.operaciones[idx])
