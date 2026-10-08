"""Pantalla de escenarios para una persona.

Los escenarios no cambian las cuotas del contrato. Solo muestran cómo podrían
verse esos mismos flujos en términos reales y, si hay un tipo de cambio de
referencia, en una referencia USD.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st

from aplicacion.consultas.escenarios_persona import (
    ResultadoEscenarioPersona,
    ServicioEscenariosPersona,
)
from dominio.escenarios import (
    EscenarioMacro,
    escenarios_predefinidos_argentina,
)
from infraestructura.db import BaseDatos

from . import componentes


def _pesos(valor: Decimal | None) -> str:
    if valor is None:
        return "—"
    negativo = valor < Decimal("0")
    entero, decimales = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{'-' if negativo else ''}$ {entero},{decimales}"


def _usd(valor: Decimal | None) -> str:
    if valor is None:
        return "No disponible"
    entero, decimales = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"USD {entero},{decimales}"


def _pct_mensual(valor: Decimal) -> str:
    return f"{valor * Decimal('100'):.2f}%"


def _fecha(fecha: date) -> str:
    return fecha.strftime("%d/%m/%Y")


def _render_explicacion() -> None:
    componentes.nota_contextual(
        (
            "Un escenario no predice el futuro ni cambia tu contrato. "
            "Solo responde cómo podrían verse los mismos cobros y pagos "
            "si se cumplieran determinados supuestos."
        ),
        "info",
    )


def _render_comparacion(
    resultados: tuple[ResultadoEscenarioPersona, ...],
) -> None:
    st.subheader("Comparación de escenarios")

    filas = []
    for resultado in resultados:
        filas.append(
            [
                resultado.nombre,
                _pct_mensual(resultado.inflacion_mensual),
                _pct_mensual(resultado.devaluacion_mensual),
                _pesos(resultado.neto_nominal),
                _pesos(resultado.neto_real),
                _usd(resultado.neto_usd),
            ]
        )

    componentes.tabla(
        [
            {"texto": "Escenario"},
            {"texto": "Inflación mensual", "alineacion": "der"},
            {"texto": "Devaluación mensual", "alineacion": "der"},
            {"texto": "Neto nominal", "alineacion": "der"},
            {"texto": "Neto a precios de hoy", "alineacion": "der"},
            {"texto": "Neto USD", "alineacion": "der"},
        ],
        filas,
    )


def _render_detalle(resultado: ResultadoEscenarioPersona) -> None:
    st.subheader(f"Escenario elegido: {resultado.nombre}")
    st.caption(resultado.descripcion)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Cobros nominales", _pesos(resultado.cobros_nominales))
    with c2:
        st.metric("Pagos nominales", _pesos(resultado.pagos_nominales))
    with c3:
        st.metric("Neto nominal", _pesos(resultado.neto_nominal))

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Cobros a precios de hoy", _pesos(resultado.cobros_reales))
    with c2:
        st.metric("Pagos a precios de hoy", _pesos(resultado.pagos_reales))
    with c3:
        st.metric("Neto a precios de hoy", _pesos(resultado.neto_real))

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Cobros en USD", _usd(resultado.cobros_usd))
    with c2:
        st.metric("Pagos en USD", _usd(resultado.pagos_usd))
    with c3:
        st.metric("Neto en USD", _usd(resultado.neto_usd))

    with st.expander("Cómo interpretar estos valores"):
        st.markdown(
            """
**Neto nominal**  
Es la diferencia entre todos los cobros y pagos del período sin ajustar por
inflación. No cambia entre escenarios porque el contrato nominal es el mismo.

**Neto a precios de hoy**  
Muestra esos mismos movimientos descontados por la inflación mensual supuesta.
Sirve para comparar el poder de compra.

**Neto USD**  
Convierte cada movimiento usando el tipo de cambio inicial indicado y la
devaluación mensual supuesta.

Ninguna de estas cifras garantiza lo que realmente ocurrirá.
"""
        )


def render(db: BaseDatos, persona_id: int) -> None:
    st.title("Escenarios")
    st.caption("Probá distintas situaciones sin cambiar el contrato.")

    _render_explicacion()

    c1, c2 = st.columns(2)
    with c1:
        horizonte = st.selectbox(
            "¿Cuántos meses querés comparar?",
            options=[3, 6, 12, 24, 36],
            index=2,
            key="escenarios_horizonte",
        )
    with c2:
        fecha_corte = st.date_input(
            "Tomar como punto de partida",
            value=date.today(),
            key="escenarios_fecha_corte",
        )

    escenarios_base = tuple(escenarios_predefinidos_argentina())
    nombres = [e.nombre for e in escenarios_base] + ["Personalizado"]
    seleccionado = st.selectbox(
        "Escenario para mirar en detalle",
        options=nombres,
        key="escenarios_seleccionado",
    )

    personalizado = None
    if seleccionado == "Personalizado":
        c1, c2 = st.columns(2)
        with c1:
            inflacion = st.number_input(
                "Inflación mensual supuesta (%)",
                min_value=-99.0,
                max_value=100.0,
                value=5.0,
                step=0.5,
                key="escenarios_inflacion_personalizado",
            )
        with c2:
            devaluacion = st.number_input(
                "Devaluación mensual supuesta (%)",
                min_value=-99.0,
                max_value=200.0,
                value=7.0,
                step=0.5,
                key="escenarios_devaluacion_personalizado",
            )

        personalizado = EscenarioMacro(
            nombre="Personalizado",
            inflacion_mensual=Decimal(str(inflacion)) / Decimal("100"),
            devaluacion_mensual=Decimal(str(devaluacion)) / Decimal("100"),
            descripcion="Supuestos definidos por vos para esta comparación.",
        )

    try:
        tc_texto = st.text_input(
            "Tipo de cambio inicial de referencia (opcional)",
            value="",
            key="escenarios_tc_inicial",
            help="Si lo dejás vacío, el sistema usa el último tipo de cambio conocido en los flujos reales, cuando existe.",
        )
        tc = Decimal(tc_texto.replace(",", ".")) if tc_texto.strip() else None

        escenarios = escenarios_base
        if personalizado is not None:
            escenarios = escenarios_base + (personalizado,)

        resultado = ServicioEscenariosPersona(db).obtener(
            persona_id,
            fecha_corte=fecha_corte,
            horizonte_meses=horizonte,
            tipo_cambio_inicial=tc,
            escenarios=escenarios,
        )
    except ValueError as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    if resultado.tipo_cambio_inicial is not None:
        componentes.nota_contextual(
            (
                f"Tipo de cambio de referencia usado: "
                f"{resultado.tipo_cambio_inicial:,.2f} ARS por USD. "
                "Es solo una referencia para el escenario."
            ),
            "info",
        )
    else:
        componentes.nota_contextual(
            "No hay un tipo de cambio de referencia disponible. Las columnas USD quedan fuera de la comparación.",
            "warning",
        )

    if not resultado.flujos_proyectados:
        componentes.estado_vacio(
            "🧭",
            "No hay movimientos futuros para comparar",
            "Cuando existan cuotas o cobros proyectados después de la fecha de corte, van a aparecer los escenarios.",
        )
        return

    _render_comparacion(resultado.resultados)

    elegido = next(
        (r for r in resultado.resultados if r.nombre == seleccionado),
        resultado.resultados[0],
    )
    _render_detalle(elegido)

    st.caption(
        (
            f"Período analizado: {_fecha(fecha_corte)} a "
            f"{_fecha(_fecha_fin(resultado.fecha_corte, resultado.horizonte_meses))}."
        )
    )


def _fecha_fin(corte: date, meses: int) -> date:
    from datetime import timedelta

    indice = corte.year * 12 + corte.month - 1 + meses + 1
    siguiente = date(indice // 12, indice % 12 + 1, 1)
    return siguiente - timedelta(days=1)
