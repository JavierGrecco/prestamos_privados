"""Administración de personas y roles."""

from __future__ import annotations

from decimal import Decimal

import streamlit as st

from aplicacion.servicios.exportaciones import ServicioExportaciones
from aplicacion.servicios.personas import (
    ESTADOS_VALIDOS,
    ROLES_ASIGNABLES,
    ROLES_VALIDOS,
    ServicioPersonas,
)
from . import componentes


ETIQUETAS_ROL = {
    "DEUDOR": "Deudor",
    "INVERSOR": "Inversor",
    "GARANTE": "Garante",
    "ADMIN": "Administración (legado; no da permisos de acceso)",
}


def _nombre(persona) -> str:
    return persona.nombre_completo or f"Persona #{persona.id}"


def _pesos(valor: Decimal) -> str:
    texto = f"{valor:,.2f}"
    return "$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _relaciones(servicio: ServicioPersonas, persona_id: int) -> None:
    componentes.render_html('<div class="seccion-titulo">Préstamos relacionados</div>')
    relaciones = servicio.prestamos_de(persona_id)
    if not relaciones:
        componentes.render_html(
            '<div class="estado-vacio-chico">Esta persona todavía no participa en préstamos.</div>'
        )
        return

    filas = []
    for r in relaciones:
        filas.append([
            r.numero,
            ETIQUETAS_ROL.get(r.rol, r.rol),
            _pesos(r.monto) if r.monto is not None else "Sin tope registrado",
            r.estado.replace("_", " ").capitalize(),
            r.destino or "—",
        ])
    componentes.tabla(
        [
            {"texto": "Préstamo"},
            {"texto": "Rol"},
            {"texto": "Capital", "alineacion": "der"},
            {"texto": "Estado"},
            {"texto": "Destino"},
        ],
        filas,
    )


def _nueva(servicio: ServicioPersonas) -> None:
    componentes.render_html('<div class="detalle-titulo">Nueva persona</div>')
    componentes.render_html(
        '<div class="saludo">Creá una persona directamente desde la aplicación.</div>'
    )

    with st.form("personas_nueva"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre *")
            apellido = st.text_input("Apellido")
            documento = st.text_input("Documento")
            telefono = st.text_input("Teléfono")
        with c2:
            email = st.text_input("Email")
            domicilio = st.text_input("Domicilio")
            roles = st.multiselect(
                "Roles financieros",
                options=list(ROLES_ASIGNABLES),
                format_func=lambda x: ETIQUETAS_ROL[x],
            )
            notas = st.text_area("Notas")

        enviar = st.form_submit_button("Crear persona", use_container_width=True)

    if not enviar:
        return

    try:
        persona_id = servicio.crear(
            nombre=nombre,
            apellido=apellido,
            documento=documento,
            telefono=telefono,
            email=email,
            domicilio=domicilio,
            notas=notas,
            roles=tuple(roles),
        )
    except Exception as exc:
        componentes.nota_contextual(str(exc), "error")
        return

    st.session_state["personas_seleccionada"] = persona_id
    componentes.disparar_nota(
        f"Persona #{persona_id} creada correctamente.",
        "success",
    )
    st.rerun()


def _administrar(servicio: ServicioPersonas) -> None:
    personas = servicio.listar()
    if not personas:
        componentes.estado_vacio(
            "👤",
            "No hay personas para administrar",
            "Creá la primera desde la pestaña Nueva persona.",
        )
        return

    opciones = {p.id: _nombre(p) for p in personas}
    actual = st.session_state.get("personas_seleccionada")
    if actual not in opciones:
        actual = personas[0].id

    persona_id = st.selectbox(
        "Persona",
        options=list(opciones),
        format_func=lambda x: opciones[x],
        index=list(opciones).index(actual),
        key="personas_seleccionada",
    )
    persona = servicio.obtener(persona_id)

    with st.form(f"personas_editar_{persona_id}"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre *", value=persona.nombre)
            apellido = st.text_input("Apellido", value=persona.apellido)
            documento = st.text_input("Documento", value=persona.documento or "")
            telefono = st.text_input("Teléfono", value=persona.telefono or "")
        with c2:
            email = st.text_input("Email", value=persona.email or "")
            domicilio = st.text_input("Domicilio", value=persona.domicilio or "")
            estado = st.selectbox(
                "Estado",
                options=list(ESTADOS_VALIDOS),
                format_func=lambda x: "Activa" if x == "ACTIVO" else "Inactiva",
                index=list(ESTADOS_VALIDOS).index(persona.estado),
            )
            notas = st.text_area("Notas", value=persona.notas or "")

        guardar = st.form_submit_button("Guardar cambios", use_container_width=True)

    if guardar:
        try:
            servicio.actualizar(
                persona_id,
                nombre=nombre,
                apellido=apellido,
                documento=documento,
                telefono=telefono,
                email=email,
                domicilio=domicilio,
                notas=notas,
            )
            servicio.cambiar_estado(persona_id, estado)
        except Exception as exc:
            componentes.nota_contextual(str(exc), "error")
        else:
            componentes.disparar_nota("Cambios guardados.", "success")
            st.rerun()

    componentes.render_html('<div class="seccion-titulo">Roles activos</div>')
    activos = set(servicio.roles(persona_id))
    roles_a_agregar = [r for r in ROLES_ASIGNABLES if r not in activos]

    c1, c2 = st.columns(2)
    with c1:
        rol = st.selectbox(
            "Agregar rol",
            options=roles_a_agregar or ["—"],
            format_func=lambda x: "No hay roles disponibles" if x == "—" else ETIQUETAS_ROL[x],
            key=f"personas_agregar_rol_{persona_id}",
        )
        if st.button(
            "Agregar rol",
            use_container_width=True,
            disabled=rol == "—",
            key=f"personas_btn_agregar_{persona_id}",
        ):
            try:
                servicio.agregar_rol(persona_id, rol)
            except Exception as exc:
                componentes.nota_contextual(str(exc), "error")
            else:
                st.rerun()

    with c2:
        quitar = st.selectbox(
            "Dar de baja",
            options=sorted(activos) or ["—"],
            format_func=lambda x: "No hay roles activos" if x == "—" else ETIQUETAS_ROL[x],
            key=f"personas_quitar_rol_{persona_id}",
        )
        motivo = st.text_input("Motivo", key=f"personas_motivo_{persona_id}")
        if st.button(
            "Dar de baja el rol",
            use_container_width=True,
            disabled=quitar == "—",
            key=f"personas_btn_quitar_{persona_id}",
        ):
            try:
                servicio.quitar_rol(persona_id, quitar, motivo=motivo)
            except Exception as exc:
                componentes.nota_contextual(str(exc), "error")
            else:
                st.rerun()

    componentes.render_html(
        "<div class='caption-ayuda'>Roles activos: "
        + (", ".join(ETIQUETAS_ROL[r] for r in sorted(activos)) if activos else "ninguno")
        + "</div>"
    )
    _relaciones(servicio, persona_id)


def _listado(servicio: ServicioPersonas, db) -> None:
    componentes.render_html('<div class="detalle-titulo">Personas</div>')
    componentes.render_html(
        '<div class="saludo">Directorio, roles y préstamos relacionados</div>'
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        estado = st.selectbox(
            "Estado",
            options=["TODAS", *ESTADOS_VALIDOS],
            format_func=lambda x: (
                "Todas" if x == "TODAS"
                else "Activas" if x == "ACTIVO"
                else "Inactivas"
            ),
            key="personas_filtro_estado",
        )
    with c2:
        rol = st.selectbox(
            "Rol",
            options=["TODOS", *ROLES_VALIDOS],
            format_func=lambda x: "Todos" if x == "TODOS" else ETIQUETAS_ROL[x],
            key="personas_filtro_rol",
        )
    with c3:
        buscar = st.text_input(
            "Buscar",
            placeholder="Nombre, apellido o documento",
            key="personas_busqueda",
        )

    personas = servicio.listar(
        estado=None if estado == "TODAS" else estado,
        rol=None if rol == "TODOS" else rol,
    )
    q = buscar.strip().lower()
    if q:
        personas = [
            p for p in personas
            if q in _nombre(p).lower()
            or q in (p.documento or "").lower()
        ]

    st.metric("Personas encontradas", len(personas))

    st.download_button(
        "Descargar personas CSV",
        data=ServicioExportaciones(db).personas_csv().encode("utf-8-sig"),
        file_name="personas.csv",
        mime="text/csv",
        key="personas_descargar_csv",
        use_container_width=True,
    )

    if not personas:
        componentes.estado_vacio("👤", "No hay coincidencias", "Probá con otros filtros.")
        return

    filas = []
    for persona in personas:
        roles = ", ".join(ETIQUETAS_ROL[r] for r in servicio.roles(persona.id)) or "Sin rol"
        filas.append([
            _nombre(persona),
            roles,
            "Activa" if persona.estado == "ACTIVO" else "Inactiva",
            persona.documento or "—",
        ])

    componentes.tabla(
        [
            {"texto": "Persona"},
            {"texto": "Roles"},
            {"texto": "Estado"},
            {"texto": "Documento"},
        ],
        filas,
    )

    seleccion = st.selectbox(
        "Seleccionar persona",
        options=[p.id for p in personas],
        format_func=lambda x: _nombre(servicio.obtener(x)),
        key="personas_seleccionada_listado",
    )
    st.session_state["personas_seleccionada"] = seleccion
    _relaciones(servicio, seleccion)


def render(db) -> None:
    componentes.renderizar_nota_pendiente()
    servicio = ServicioPersonas(db)
    tabs = st.tabs(["Personas", "Nueva persona", "Administrar"])
    with tabs[0]:
        _listado(servicio, db)
    with tabs[1]:
        _nueva(servicio)
    with tabs[2]:
        _administrar(servicio)
