"""Pantalla M7 de comparación de decisiones financieras."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st

from aplicacion.consultas.comparador_decisiones_financieras import (
    AlternativaComparada,
    ComparacionDecisionesFinancieras,
    ServicioComparadorDecisionesFinancieras,
)
from infraestructura.db import BaseDatos

from . import componentes


def _pesos(valor: Decimal | None) -> str:
    if valor is None:
        return "No disponible"
    negativo = valor < Decimal("0")
    entero, decimales = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{'-' if negativo else ''}$ {entero},{decimales}"


def _pct(valor: Decimal | None) -> str:
    if valor is None:
        return "No disponible"
    return f"{valor * Decimal('100'):.2f}%"


def _fecha(fecha: date | None) -> str:
    return fecha.strftime("%d/%m/%Y") if fecha else "—"


def _etiqueta(alternativa: AlternativaComparada) -> str:
    destino = alternativa.destino or "sin destino"
    return f"{alternativa.prestamo_numero} · {alternativa.rol.lower()} · {destino}"


def _render_explicacion() -> None:
    componentes.nota_contextual(
        (
            "Esta pantalla no decide por vos. Ordena operaciones que ya existen "
            "para que puedas comparar capital, movimientos, valor futuro y "
            "rendimiento usando la misma fecha y los mismos supuestos."
        ),
        "info",
    )


def _render_homogeneidad(comparacion: ComparacionDecisionesFinancieras) -> None:
    if comparacion.homogenea:
        componentes.nota_contextual(
            (
                "Las alternativas usan la misma moneda, rol y reglas principales "
                "de amortización. La comparación es homogénea."
            ),
            "success",
        )
        return

    componentes.nota_contextual(
        (
            "Las alternativas no son completamente homogéneas. Podés "
            "compararlas, pero estas diferencias cambian cómo conviene "
            "interpretar el resultado."
        ),
        "warning",
    )
    for motivo in comparacion.motivos_no_homogeneidad:
        st.write(f"• {motivo}")


def _render_tabla(comparacion: ComparacionDecisionesFinancieras) -> None:
    filas = []
    for a in comparacion.alternativas:
        filas.append(
            [
                _etiqueta(a),
                a.estado,
                _pesos(a.capital_referencia),
                _pesos(a.flujo_real_neto),
                _pesos(a.flujo_futuro_neto),
                _pesos(a.valor_real_futuro),
                _pct(a.rendimiento_anualizado),
                _pct(a.rendimiento_real),
            ]
        )

    componentes.tabla(
        [
            {"texto": "Alternativa"},
            {"texto": "Estado"},
            {"texto": "Capital", "alineacion": "der"},
            {"texto": "Flujo real", "alineacion": "der"},
            {"texto": "Flujo futuro", "alineacion": "der"},
            {"texto": "Valor real futuro", "alineacion": "der"},
            {"texto": "Rend./costo anual", "alineacion": "der"},
            {"texto": "Rend./costo real", "alineacion": "der"},
        ],
        filas,
    )


def _render_detalle(alternativa: AlternativaComparada) -> None:
    st.subheader(f"Detalle: {_etiqueta(alternativa)}")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Capital de referencia", _pesos(alternativa.capital_referencia))
    with c2:
        st.metric("Flujo real", _pesos(alternativa.flujo_real_neto))
    with c3:
        st.metric("Flujo futuro", _pesos(alternativa.flujo_futuro_neto))

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Valor real futuro", _pesos(alternativa.valor_real_futuro))
    with c2:
        st.metric(
            "Rendimiento / costo anualizado",
            _pct(alternativa.rendimiento_anualizado),
        )
    with c3:
        st.metric(
            "Resultado real anualizado",
            _pct(alternativa.rendimiento_real),
        )

    with st.expander("Condiciones de la alternativa"):
        st.markdown(
            f"""
**Moneda:** {alternativa.moneda}

**Tasa anual registrada:** {_pct(alternativa.tasa_anual)}

**Modalidad:** {alternativa.modalidad_tasa or "No disponible"}

**Sistema:** {alternativa.sistema}

**Convención de días:** {alternativa.convencion_dias}

**Inicio:** {_fecha(alternativa.fecha_inicio)}

**Movimientos reales usados:** {alternativa.cantidad_flujos_reales}

**Movimientos futuros usados:** {alternativa.cantidad_flujos_futuros}
"""
        )


def render(db: BaseDatos, persona_id: int) -> None:
    st.title("Comparar")
    st.caption(
        "Compará dos o más operaciones registradas sin convertir la aplicación "
        "en un asesor automático."
    )

    _render_explicacion()

    servicio = ServicioComparadorDecisionesFinancieras(db)

    try:
        disponibles = servicio.listar_alternativas(persona_id)
    except ValueError as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    if len(disponibles) < 2:
        componentes.estado_vacio(
            "⚖️",
            "Todavía no hay dos operaciones para comparar",
            (
                "Cuando registres al menos dos préstamos o inversiones, "
                "vas a poder compararlos acá."
            ),
        )
        return

    etiquetas = {a.clave: a.etiqueta for a in disponibles}
    claves = [a.clave for a in disponibles]

    seleccionadas = st.multiselect(
        "Elegí las operaciones",
        options=claves,
        default=claves[:2],
        format_func=lambda clave: etiquetas[clave],
        max_selections=6,
        key="comparador_alternativas",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        horizonte = st.selectbox(
            "Horizonte futuro",
            options=[3, 6, 12, 24, 36],
            index=2,
            key="comparador_horizonte",
        )
    with c2:
        fecha_corte = st.date_input(
            "Fecha de corte",
            value=date.today(),
            key="comparador_fecha_corte",
        )
    with c3:
        inflacion_pct = st.number_input(
            "Inflación mensual (%)",
            min_value=-99.0,
            max_value=100.0,
            value=5.0,
            step=0.5,
            key="comparador_inflacion",
        )

    if len(seleccionadas) < 2:
        componentes.nota_contextual(
            "Elegí al menos dos alternativas para iniciar la comparación.",
            "info",
        )
        return

    try:
        comparacion = servicio.comparar(
            persona_id,
            tuple(seleccionadas),
            fecha_corte=fecha_corte,
            horizonte_meses=horizonte,
            inflacion_mensual_supuesto=(
                Decimal(str(inflacion_pct)) / Decimal("100")
            ),
        )
    except ValueError as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    componentes.nota_contextual(
        (
            f"Comparación al {_fecha(comparacion.fecha_corte)}, con horizonte de "
            f"{comparacion.horizonte_meses} meses y una inflación supuesta de "
            f"{_pct(comparacion.inflacion_mensual_supuesto)} mensual."
        ),
        "info",
    )

    _render_homogeneidad(comparacion)
    _render_tabla(comparacion)

    seleccionado = st.selectbox(
        "Mirar una alternativa en detalle",
        options=list(range(len(comparacion.alternativas))),
        format_func=lambda i: _etiqueta(comparacion.alternativas[i]),
        key="comparador_detalle",
    )
    _render_detalle(comparacion.alternativas[seleccionado])

    with st.expander("Cómo leer la comparación"):
        st.markdown(
            """
**Capital**: monto de referencia de la operación. Para una inversión es el
capital aportado registrado; para una deuda es el capital original.

**Flujo real**: entradas menos salidas que ya ocurrieron, vistos desde tu rol.

**Flujo futuro**: entradas menos salidas proyectadas dentro del mismo horizonte.

**Valor real futuro**: esos mismos movimientos futuros expresados a precios de
hoy según la inflación supuesta.

**Rendimiento / costo anualizado**: XIRR de los movimientos reales cuando hay
evidencia suficiente. Si no se puede calcular, se muestra como no disponible.

**Resultado real anualizado**: rendimiento anualizado ajustado por la inflación
elegida, siempre que exista XIRR.

Las cifras ayudan a comparar. No indican automáticamente cuál alternativa es
mejor para vos.
"""
        )
