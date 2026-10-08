"""
Punto de entrada de la aplicación.

Ejecutar:
    streamlit run ui/app.py

Al arrancar, aplica las migraciones pendientes. Así el schema
siempre está actualizado sin tener que correr scripts a mano.
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from infraestructura.db import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo

from ui.estilos import aplicar_estilos
from ui.navegacion import renderizar_navegacion
from ui.pagina_principal import render as render_principal
from ui.pagina_prestamos import render as render_prestamos
from ui.pagina_motor_v3 import render as render_motor_v3
from ui.pagina_analisis import render as render_analisis
from ui.pagina_pagos import render as render_pagos
from ui.pagina_operacion import render as render_operacion
from ui.pagina_detalle_financiero import render as render_detalle_financiero
from ui.personas_view import render as render_personas
from ui import componentes


st.set_page_config(
    page_title="Mis Préstamos",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inicializar_estado() -> None:
    if "tema" not in st.session_state:
        st.session_state["tema"] = "claro"
    if "nivel_detalle" not in st.session_state:
        st.session_state["nivel_detalle"] = "simple"
    if "persona_id" not in st.session_state:
        st.session_state["persona_id"] = None
    if "motor_pago_modo_solicitado" not in st.session_state:
        st.session_state["motor_pago_modo_solicitado"] = "SOMBRA"
    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "resumen"
    if st.session_state.get("nivel_detalle") not in ("simple", "detallado"):
        st.session_state["nivel_detalle"] = "simple"


def ruta_base_datos() -> Path:
    """Devuelve la base configurada o la base local por defecto."""
    configurada = os.environ.get("PRESTAMOS_DB_PATH")
    if configurada:
        return Path(configurada).expanduser().resolve()
    return RAIZ / "datos" / "prestamos.db"


@st.cache_resource
def abrir_db(ruta: str) -> BaseDatos:
    """
    Abre la base y aplica migraciones pendientes.

    IMPORTANTE: se aplican migraciones acá porque el schema
    evoluciona con cada versión, y no queremos obligar al usuario
    a correr un script cada vez que actualizamos el código.
    """
    db = BaseDatos(ruta)
    db.abrir()

    # Aplicar migraciones pendientes (silenciosamente)
    try:
        aplicar_migraciones(db)
    except Exception as e:
        # Una base con schema incompleto no es un estado operativo válido.
        db.cerrar()
        st.error(f"Error al aplicar migraciones: {e}")
        st.stop()

    return db


ICONO_TEMA = {
    "claro": "☀️",
    "intermedio": "📖",
    "oscuro": "🌙",
}


def renderizar_barra_superior(db: BaseDatos) -> None:
    personas_repo = PersonaRepo(db)
    personas = personas_repo.listar()

    if st.session_state["persona_id"] is None:
        javier = next(
            (p for p in personas if p.nombre.lower() == "javier"),
            personas[0],
        )
        st.session_state["persona_id"] = javier.id

    col_nav, col_resto = st.columns([2, 3])
    with col_nav:
        renderizar_navegacion()

    with col_resto:
        col_persona, col_tema = st.columns([2, 1])

        with col_persona:
            if personas:
                componentes.render_html(
                    '<div class="etiqueta-control">Persona</div>'
                )
                opciones = {p.id: f"{p.nombre} {p.apellido}".strip() for p in personas}
                ids = list(opciones.keys())
                idx = (
                    ids.index(st.session_state["persona_id"])
                    if st.session_state["persona_id"] in ids
                    else 0
                )
                st.selectbox(
                    "Persona",
                    options=ids,
                    format_func=lambda x: opciones[x],
                    index=idx,
                    label_visibility="collapsed",
                    key="persona_id",
                )
            else:
                componentes.render_html(
                    '<div class="etiqueta-control">Persona</div>'
                    '<div class="caption-ayuda">Creá la primera persona desde Personas.</div>'
                )

        with col_tema:
            componentes.render_html(
                '<div class="etiqueta-control">Tema</div>'
            )
            st.segmented_control(
                "Tema",
                options=["claro", "intermedio", "oscuro"],
                format_func=lambda x: ICONO_TEMA[x],
                default=st.session_state["tema"],
                label_visibility="collapsed",
                key="tema",
            )


def main() -> None:
    inicializar_estado()
    aplicar_estilos(st.session_state["tema"])

    db = abrir_db(str(ruta_base_datos()))
    personas = PersonaRepo(db).listar()

    pagina_pendiente = st.session_state.pop("pagina_pendiente", None)
    if pagina_pendiente in {
        "resumen",
        "prestamos",
        "motor_v3",
        "analisis",
        "pagos",
        "operacion",
        "detalle_financiero",
        "personas",
    }:
        # Debe resolverse antes de crear el segmented_control que usa la misma
        # clave "pagina". De lo contrario Streamlit no permite modificar su
        # valor después de instanciar el widget durante el rerun.
        st.session_state["pagina"] = pagina_pendiente

    renderizar_barra_superior(db)

    componentes.render_html(
        "<hr style='border: none; border-top: 1px solid var(--border); "
        "margin: 1.5rem 0 2rem 0;'>"
    )

    pagina = st.session_state.get("pagina", "resumen")

    if pagina == "personas":
        render_personas(db)
    elif not personas:
        componentes.estado_vacio(
            icono="🌱",
            titulo="Todavía no hay personas cargadas",
            texto="Empezá por crear una persona en la sección Personas.",
        )
        return
    elif pagina == "prestamos":
        render_prestamos(db, st.session_state["persona_id"])
    elif pagina == "motor_v3":
        render_motor_v3(db)
    elif pagina == "analisis":
        render_analisis(db, st.session_state["persona_id"])
    elif pagina == "pagos":
        render_pagos(
            db,
            st.session_state["persona_id"],
            st.session_state.get("prestamo_seleccionado"),
        )
    elif pagina == "operacion":
        render_operacion(db)
    elif pagina == "detalle_financiero":
        prestamo_id = st.session_state.get("prestamo_seleccionado")
        if prestamo_id:
            render_detalle_financiero(db, prestamo_id)
        else:
            st.session_state["pagina_pendiente"] = "prestamos"
            st.rerun()
    else:
        render_principal(
            db,
            st.session_state["persona_id"],
            st.session_state["nivel_detalle"] or "simple",
        )


if __name__ == "__main__":
    main()