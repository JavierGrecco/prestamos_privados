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
from ui.pagina_planificar import render as render_planificar
from ui.pagina_escenarios import render as render_escenarios
from ui.pagina_rendimiento import render as render_rendimiento
from ui.pagina_reportes import render as render_reportes
from ui.pagina_mi_espacio import render as render_mi_espacio
from ui.pagina_prestamos import render as render_prestamos
from ui.pagina_motor_v3 import render as render_motor_v3
from ui.pagina_analisis import render as render_analisis
from ui.pagina_pagos import render as render_pagos
from ui.pagina_operacion import render as render_operacion
from ui.pagina_detalle_financiero import render as render_detalle_financiero
from ui.personas_view import render as render_personas
from ui.pagina_auditoria import render as render_auditoria
from ui import componentes
from ui.contexto_operador import inicializar_operador, operador_actual
from aplicacion.seguridad.acceso_personas import (
    AccesoPersonaDenegado,
    PoliticaAccesoPersonas,
    estado_ux_acceso,
)
from aplicacion.seguridad.capacidades import (
    CAP_OPERAR,
    CAP_VER_AUDITORIA,
    CAP_VER_MOTOR_V3,
    CAP_VER_PERSONAS,
    PoliticaCapacidades,
)
from aplicacion.seguridad.contexto_sesion import ServicioContextoSesionSeguridad
from aplicacion.seguridad.identidad import (
    ProveedorIdentidadLocal,
    descripcion_identidad,
)


st.set_page_config(
    page_title="Mis Préstamos",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inicializar_estado() -> None:
    inicializar_operador()
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


def renderizar_barra_superior(db: BaseDatos) -> list:
    personas_repo = PersonaRepo(db)
    personas = personas_repo.listar()
    politica = PoliticaAccesoPersonas.desde_entorno()
    personas_autorizadas = [
        p for p in personas if politica.puede_consultar(p.id)
    ]

    if personas and not personas_autorizadas:
        st.session_state["persona_id"] = None
    elif personas_autorizadas and (
        st.session_state["persona_id"] is None
        or not politica.puede_consultar(st.session_state["persona_id"])
    ):
        javier = next(
            (p for p in personas_autorizadas if p.nombre.lower() == "javier"),
            personas_autorizadas[0],
        )
        st.session_state["persona_id"] = javier.id

    col_nav, col_resto = st.columns([2, 3])
    with col_nav:
        renderizar_navegacion()

    with col_resto:
        col_persona, col_operador, col_tema = st.columns([2, 2, 1])

        with col_persona:
            if personas_autorizadas:
                componentes.render_html(
                    '<div class="etiqueta-control">Persona autorizada</div>'
                )
                opciones = {
                    p.id: f"{p.nombre} {p.apellido}".strip()
                    for p in personas_autorizadas
                }
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
                if personas:
                    componentes.render_html(
                        '<div class="etiqueta-control">Persona autorizada</div>'
                        '<div class="caption-ayuda">Esta sesión no tiene personas autorizadas para consultar.</div>'
                    )
                else:
                    componentes.render_html(
                        '<div class="etiqueta-control">Persona</div>'
                        '<div class="caption-ayuda">Creá la primera persona desde Personas.</div>'
                    )

        with col_operador:
            componentes.render_html('<div class="etiqueta-control">Operador declarado</div>')
            st.text_input(
                "Operador",
                value=operador_actual(),
                key="operador",
                label_visibility="collapsed",
                help="Identidad declarada para la auditoría de esta sesión; no reemplaza autenticación.",
            )

        contexto_seguridad = ServicioContextoSesionSeguridad(
            ProveedorIdentidadLocal(),
            politica,
        ).construir(
            actor_declarado=operador_actual(),
            persona_id=st.session_state.get("persona_id"),
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

        titulo_acceso, mensaje_acceso = estado_ux_acceso(politica)
        tipo_acceso = "warning" if not politica.autenticacion_real else "success"
        componentes.nota_contextual(
            f"{titulo_acceso}: {mensaje_acceso}",
            tipo_acceso,
        )
        componentes.nota_contextual(
            descripcion_identidad(contexto_seguridad.identidad),
            "warning" if not contexto_seguridad.autenticada else "success",
        )
        politica_capacidades = PoliticaCapacidades()
        componentes.nota_contextual(
            "Rol de sesión: "
            + politica_capacidades.descripcion_roles(
                contexto_seguridad.identidad
            ),
            "info",
        )

    return personas_autorizadas


def main() -> None:
    inicializar_estado()
    aplicar_estilos(st.session_state["tema"])

    db = abrir_db(str(ruta_base_datos()))
    personas = PersonaRepo(db).listar()

    pagina_pendiente = st.session_state.pop("pagina_pendiente", None)
    if pagina_pendiente in {
        "resumen",
        "mi_espacio",
        "planificar",
        "escenarios",
        "rendimiento",
        "reportes",
        "prestamos",
        "motor_v3",
        "analisis",
        "pagos",
        "operacion",
        "detalle_financiero",
        "personas",
        "auditoria",
    }:
        # Debe resolverse antes de crear el segmented_control que usa la misma
        # clave "pagina". De lo contrario Streamlit no permite modificar su
        # valor después de instanciar el widget durante el rerun.
        st.session_state["pagina"] = pagina_pendiente

    personas_visibles = renderizar_barra_superior(db)

    politica = PoliticaAccesoPersonas.desde_entorno()
    politica_capacidades = PoliticaCapacidades()
    identidad = ProveedorIdentidadLocal().obtener_identidad()

    paginas_con_persona = {
        "resumen",
        "mi_espacio",
        "planificar",
        "escenarios",
        "rendimiento",
        "reportes",
        "prestamos",
        "analisis",
        "pagos",
        "detalle_financiero",
    }

    capacidades_por_pagina = {
        "personas": CAP_VER_PERSONAS,
        "auditoria": CAP_VER_AUDITORIA,
        "motor_v3": CAP_VER_MOTOR_V3,
        "operacion": CAP_OPERAR,
    }
    pagina_actual = st.session_state.get("pagina", "resumen")
    if pagina_actual in capacidades_por_pagina:
        capacidad = capacidades_por_pagina[pagina_actual]
        try:
            politica_capacidades.exigir(identidad, capacidad)
        except PermissionError as exc:
            componentes.nota_contextual(str(exc), "error")
            return

    if pagina_actual in paginas_con_persona:
        persona_id = st.session_state.get("persona_id")
        if persona_id is None:
            componentes.nota_contextual(
                "No hay una persona autorizada para esta pantalla.",
                "error",
            )
            return
        try:
            ServicioContextoSesionSeguridad(
                ProveedorIdentidadLocal(),
                politica,
            ).construir(
                actor_declarado=operador_actual(),
                persona_id=persona_id,
            )
        except AccesoPersonaDenegado as exc:
            componentes.nota_contextual(str(exc), "error")
            return

    componentes.render_html(
        "<hr style='border: none; border-top: 1px solid var(--border); "
        "margin: 1.5rem 0 2rem 0;'>"
    )

    pagina = st.session_state.get("pagina", "resumen")

    if pagina == "personas":
        render_personas(db)
    elif pagina == "auditoria":
        render_auditoria(db)
    elif not personas_visibles and pagina in paginas_con_persona:
        componentes.estado_vacio(
            icono="🌱",
            titulo="Todavía no hay personas cargadas",
            texto="Empezá por crear una persona en la sección Personas.",
        )
        return
    elif pagina == "mi_espacio":
        render_mi_espacio(db, st.session_state["persona_id"])
    elif pagina == "planificar":
        render_planificar(db, st.session_state["persona_id"])
    elif pagina == "escenarios":
        render_escenarios(db, st.session_state["persona_id"])
    elif pagina == "rendimiento":
        render_rendimiento(db, st.session_state["persona_id"])
    elif pagina == "reportes":
        render_reportes(db, st.session_state["persona_id"])
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
        try:
            PoliticaAccesoPersonas.desde_entorno().autorizar(
                st.session_state["persona_id"],
                actor_declarado=operador_actual(),
            )
        except AccesoPersonaDenegado as exc:
            componentes.nota_contextual(str(exc), "error")
            return
        render_principal(
            db,
            st.session_state["persona_id"],
            st.session_state["nivel_detalle"] or "simple",
        )


if __name__ == "__main__":
    main()