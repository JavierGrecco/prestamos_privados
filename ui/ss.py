"""
Pantalla principal del sistema.

Es la primera pantalla que ve el usuario al abrir la app. Responde
a la promesa del sistema: "un número que te dice si tu plata está
ganando o perdiendo".

Dos niveles de detalle:
  - Simple:    el número grande + el "por qué".
  - Detallado: todo lo de simple + las métricas numéricas.

Todo el HTML se renderiza con componentes.render_html().
"""
import html

import streamlit as st

from infraestructura.db import BaseDatos
from infraestructura.repositorios import PersonaRepo

from .metricas import (
    calcular_metricas,
    formatear_pesos_con_signo,
    formatear_pesos,
    color_para_veredicto,
    emoji_para_veredicto,
)
from . import componentes


def _toggle_nivel() -> None:
    actual = st.session_state.get("nivel_detalle", "simple")
    st.session_state["nivel_detalle"] = (
        "detallado" if actual == "simple" else "simple"
    )


def _simular_escenario() -> None:
    componentes.disparar_nota(
        "El simulador estará disponible próximamente.",
        "info",
    )


def render(
    db: BaseDatos,
    persona_id: int,
    nivel_detalle: str = "simple",
) -> None:
    es_detallado = nivel_detalle != "simple"

    persona_repo = PersonaRepo(db)
    persona = persona_repo.obtener(persona_id)
    if persona is None:
        componentes.render_html("No se encontró la persona.")
        return

    componentes.render_html(
        f'<div class="saludo">Hola, {html.escape(persona.nombre, quote=True)} 👋</div>'
    )

    metricas = calcular_metricas(db, persona_id)

    color = color_para_veredicto(metricas.veredicto)
    emoji = emoji_para_veredicto(metricas.veredicto)

    if "creciendo" in metricas.mensaje_principal:
        palabra = "Creciendo"
    elif "achicando" in metricas.mensaje_principal:
        palabra = "Achicándose"
    else:
        palabra = "Estable"

    componentes.render_html(f"""
        <div class="bloque-principal">
            <div class="etiqueta">Este año tu plata</div>
            <div class="veredicto {color}">{palabra}</div>
            <div class="numero {color}">{formatear_pesos_con_signo(metricas.efecto_neto)}</div>
            <div class="subtexto">en poder de compra, no en pesos</div>
            <span class="emoji-veredicto">{emoji}</span>
        </div>
    """)

    componentes.render_html(
        '<div class="seccion-titulo">Cómo se explica</div>'
    )

    if metricas.capital_invertido > 0:
        componentes.render_html(f"""
            <div class="tarjeta-porque">
                <div class="icono">💰</div>
                <div class="texto">
                    <div class="titulo">Tenés {formatear_pesos(metricas.capital_invertido)} invertidos</div>
                    <div class="detalle">{html.escape(metricas.detalle_inversion, quote=True)}</div>
                </div>
            </div>
        """)

    if metricas.capital_adeudado > 0:
        componentes.render_html(f"""
            <div class="tarjeta-porque">
                <div class="icono">🏠</div>
                <div class="texto">
                    <div class="titulo">Debés {formatear_pesos(metricas.capital_adeudado)}</div>
                    <div class="detalle">{html.escape(metricas.detalle_deuda, quote=True)}</div>
                </div>
            </div>
        """)

    if es_detallado:
        componentes.render_html(
            '<div class="seccion-titulo">Números en detalle</div>'
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Invertido", formatear_pesos(metricas.capital_invertido))
        with col2:
            st.metric("Adeudado", formatear_pesos(metricas.capital_adeudado))
        with col3:
            st.metric(
                "Efecto neto anual",
                formatear_pesos_con_signo(metricas.efecto_neto),
            )

        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Efecto de la inversión",
                formatear_pesos_con_signo(metricas.efecto_inversion),
            )
        with col2:
            st.metric(
                "Efecto de la deuda (licuación)",
                formatear_pesos_con_signo(metricas.efecto_deuda),
            )

        st.caption(
            f"Inflación mensual usada en el cálculo: "
            f"{float(metricas.inflacion_mensual)*100:.1f}%"
        )

    componentes.render_html("<br>")

    _, col_nivel, col_simular, _ = st.columns([1, 2, 2, 1])

    with col_nivel:
        st.button(
            "Ver más detalle" if not es_detallado else "Volver a simple",
            use_container_width=True,
            on_click=_toggle_nivel,
            key="btn_nivel",
        )

    with col_simular:
        st.button(
            "Simular escenario",
            use_container_width=True,
            on_click=_simular_escenario,
            key="btn_simular",
        )
        componentes.renderizar_nota_pendiente()