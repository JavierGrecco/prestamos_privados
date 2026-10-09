"""
Punto de entrada de la aplicación.

Ejecutar:
    streamlit run ui/app.py

Al arrancar, inicializa las bases vacías. Las actualizaciones de una base
existente requieren inspección y migración explícita con backup verificado.
"""
import os
import shlex
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from infraestructura.db import BaseDatos
from infraestructura.migraciones import (
    aplicar_migraciones,
    inspeccionar_estado_migraciones,
)
from infraestructura.repositorios import PersonaRepo

from ui.estilos import aplicar_estilos
from ui.navegacion import (
    PAGINAS_POR_CLAVE,
    capacidad_requerida_para_pagina,
    paginas_permitidas_para,
    renderizar_navegacion,
    requiere_persona_para_pagina,
)
from ui.pagina_principal import render as render_principal
from ui.pagina_planificar import render as render_planificar
from ui.pagina_escenarios import render as render_escenarios
from ui.pagina_rendimiento import render as render_rendimiento
from ui.pagina_reportes import render as render_reportes
from ui.pagina_comparador import render as render_comparador
from ui.pagina_mi_espacio import render as render_mi_espacio
from ui.pagina_prestamos import render as render_prestamos
from ui.pagina_motor_v3 import render as render_motor_v3
from ui.pagina_analisis import render as render_analisis
from ui.pagina_pagos import render as render_pagos
from ui.pagina_operacion import render as render_operacion
from ui.pagina_detalle_financiero import render as render_detalle_financiero
from ui.personas_view import render as render_personas
from ui.pagina_usuarios import render as render_usuarios
from ui.autenticacion_local import obtener_usuario_autenticado
from ui.pagina_auditoria import render as render_auditoria
from ui import componentes
from ui.contexto_operador import inicializar_operador, operador_actual
from aplicacion.seguridad.acceso_personas import (
    AccesoPersonaDenegado,
    PoliticaAccesoPersonas,
    estado_ux_acceso,
)
from aplicacion.seguridad.capacidades import (
    CAP_CONFIGURAR_MOTOR_V3,
    PoliticaCapacidades,
)
from aplicacion.seguridad.contexto_sesion import ServicioContextoSesionSeguridad
from aplicacion.seguridad.identidad import (
    ProveedorIdentidadUsuarioLocal,
    descripcion_identidad,
)


st.set_page_config(
    page_title="Mis Préstamos",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inicializar_estado() -> None:
    inicializar_operador()
    if "tema" not in st.session_state:
        # Tema preferido del producto: mantener oscuro como predeterminado.
        st.session_state["tema"] = "oscuro"
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
    """Abre la base y evita upgrades silenciosos de bases existentes."""
    db = BaseDatos(ruta)
    db.abrir()

    try:
        estado = inspeccionar_estado_migraciones(db)
    except Exception:
        db.cerrar()
        componentes.nota_contextual(
            "No se pudo inspeccionar el historial de migraciones. "
            "La aplicación se detuvo para evitar operar sobre una base "
            "cuyo estado no se pudo verificar.",
            "error",
        )
        st.stop()

    if not estado.historial_valido:
        db.cerrar()
        componentes.nota_contextual(
            "No se puede abrir esta base con seguridad porque su historial "
            "de migraciones no es válido. No se modificó el esquema. "
            "Revisá una copia y el historial antes de continuar.",
            "error",
        )
        st.stop()

    if estado.es_base_nueva:
        # El primer arranque local puede preparar una base vacía sin exigir
        # pasos manuales. Esto no se aplica a bases con datos existentes.
        try:
            aplicar_migraciones(db)
        except Exception as e:
            db.cerrar()
            componentes.nota_contextual(
                f"No se pudo inicializar la base nueva: {e}",
                "error",
            )
            st.stop()
        return db

    if estado.pendientes:
        origen = estado.version_actual
        destino = estado.version_destino
        cantidad = len(estado.pendientes)
        primera = estado.pendientes[0]
        ultima = estado.pendientes[-1]
        db.cerrar()
        componentes.nota_contextual(
            f"La base necesita una actualización de esquema "
            f"(v{origen} → v{destino}; {cantidad} migraciones pendientes). "
            "No se aplicó ningún cambio al abrir la aplicación.",
            "warning",
        )
        st.info(
            "Antes de actualizar una base existente, generá un backup "
            "verificado. El comando crea una copia nueva, comprueba su "
            "integridad y recién entonces aplica las migraciones."
        )
        comando = (
            f"python -m scripts.migrar_base {shlex.quote(ruta)} "
            "--aplicar --backup /ruta/segura/backup-pre-migracion.db"
        )
        st.code(comando, language="bash")
        st.caption(
            f"Pendientes desde {primera.version:03d} ({primera.nombre}) "
            f"hasta {ultima.version:03d} ({ultima.nombre}). Elegí una ruta "
            "de backup que todavía no exista."
        )
        st.stop()

    return db


ICONO_TEMA = {
    "claro": "☀️",
    "intermedio": "📖",
    "oscuro": "🌙",
}


def renderizar_barra_superior(db: BaseDatos, usuario_actual) -> list:
    personas_repo = PersonaRepo(db)
    personas = personas_repo.listar()
    politica = PoliticaAccesoPersonas.desde_entorno()
    personas_autorizadas = [
        p for p in personas if politica.puede_consultar(p.id)
    ]

    ids_personas_autorizadas = {p.id for p in personas_autorizadas}
    if st.session_state.get("persona_id") not in ids_personas_autorizadas:
        # No asumir que el usuario quiere consultar a Javier ni a la primera
        # persona de la lista. La selección pertenece al contexto de trabajo.
        st.session_state["persona_id"] = None

    proveedor_identidad = ProveedorIdentidadUsuarioLocal(
        usuario_id=usuario_actual.id,
        username=usuario_actual.username,
        nombre=usuario_actual.nombre,
        rol=usuario_actual.rol,
    )
    identidad_nav = proveedor_identidad.obtener_identidad()
    politica_nav = PoliticaCapacidades()
    paginas_permitidas = paginas_permitidas_para(identidad_nav, politica_nav)
    renderizar_navegacion(paginas_permitidas)

    with st.container():
        col_persona, col_operador, col_tema = st.columns([2, 2, 1])

        with col_persona:
            if st.session_state.get("pagina") == "mi_espacio":
                componentes.render_html(
                    '<div class="etiqueta-control">Mi persona</div>'
                )
                persona_vinculada = next(
                    (p for p in personas if p.id == usuario_actual.persona_id),
                    None,
                )
                if usuario_actual.persona_id is None:
                    componentes.render_html(
                        '<div class="caption-ayuda">Cuenta sin persona vinculada</div>'
                    )
                elif persona_vinculada is None or not politica.puede_consultar(persona_vinculada.id):
                    componentes.render_html(
                        '<div class="caption-ayuda">La persona vinculada no está en el alcance autorizado.</div>'
                    )
                else:
                    componentes.render_html(
                        '<div class="persona-contexto-fijo">'
                        + componentes.escapar_texto_html(persona_vinculada.nombre_completo)
                        + '</div>'
                    )
            elif personas_autorizadas:
                componentes.render_html(
                    '<div class="etiqueta-control">Persona en contexto</div>'
                )
                opciones = {
                    p.id: f"{p.nombre} {p.apellido}".strip()
                    for p in personas_autorizadas
                }
                ids = [None, *opciones.keys()]
                persona_seleccionada = st.session_state.get("persona_id")
                idx = (
                    ids.index(persona_seleccionada)
                    if persona_seleccionada in ids
                    else 0
                )
                st.selectbox(
                    "Persona",
                    options=ids,
                    format_func=lambda x: (
                        "Seleccioná una persona" if x is None else opciones[x]
                    ),
                    index=idx,
                    label_visibility="collapsed",
                    key="persona_id",
                )
            else:
                if personas:
                    componentes.render_html(
                        '<div class="etiqueta-control">Persona en contexto</div>'
                        '<div class="caption-ayuda">Esta sesión no tiene personas autorizadas para consultar.</div>'
                    )
                else:
                    componentes.render_html(
                        '<div class="etiqueta-control">Persona</div>'
                        '<div class="caption-ayuda">Creá la primera persona desde Personas.</div>'
                    )

        with col_operador:
            componentes.render_html('<div class="etiqueta-control">Cuenta activa</div>')
            st.markdown(f"**{usuario_actual.nombre}**")
            st.caption(f"@{usuario_actual.username} · {usuario_actual.rol}")
            if st.button("Cerrar sesión", key="cerrar_sesion_local"):
                st.session_state.pop("usuario_app_id", None)
                st.session_state.pop("usuario_app_revision", None)
                st.session_state.pop("operador", None)
                st.rerun()


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

        if politica.modo == "ALLOWLIST":
            titulo_acceso, mensaje_acceso = estado_ux_acceso(politica)
            componentes.nota_contextual(
                f"{titulo_acceso}: {mensaje_acceso}",
                "info",
            )
        else:
            componentes.nota_contextual(
                "Cuenta autenticada localmente. La autorización de las "
                "pantallas se resuelve según el rol de esta cuenta.",
                "success",
            )
        componentes.nota_contextual(
            descripcion_identidad(identidad_nav),
            "warning" if not identidad_nav.autenticada else "success",
        )
        politica_capacidades = PoliticaCapacidades()
        componentes.nota_contextual(
            "Rol de sesión: "
            + politica_capacidades.descripcion_roles(
                identidad_nav
            ),
            "info",
        )

    return personas_autorizadas


def main() -> None:
    modo_autenticacion = os.environ.get("PRESTAMOS_AUTH_MODE", "local").strip().lower()
    if modo_autenticacion != "local":
        st.error(
            "El modo de autenticación solicitado no está implementado en esta "
            "versión. El acceso disponible es exclusivamente local; no expongas "
            "esta instancia a Internet."
        )
        st.stop()

    inicializar_estado()
    aplicar_estilos(st.session_state["tema"])

    db = abrir_db(str(ruta_base_datos()))
    usuario_actual = obtener_usuario_autenticado(db)
    if usuario_actual is None:
        return

    # El actor de auditoría proviene de la cuenta autenticada; ya no se puede
    # cambiar desde un campo de texto para aparentar otra identidad.
    st.session_state["operador"] = usuario_actual.username
    proveedor_identidad = ProveedorIdentidadUsuarioLocal(
        usuario_id=usuario_actual.id,
        username=usuario_actual.username,
        nombre=usuario_actual.nombre,
        rol=usuario_actual.rol,
    )
    identidad = proveedor_identidad.obtener_identidad()
    personas = PersonaRepo(db).listar()

    pagina_pendiente = st.session_state.pop("pagina_pendiente", None)
    if pagina_pendiente in PAGINAS_POR_CLAVE:
        # Aplicar la ruta antes de renderizar la navegación. Esto permite
        # abrir rutas contextuales (por ejemplo, el detalle desde un préstamo)
        # sin agregar esas rutas al menú raíz.
        st.session_state["pagina"] = pagina_pendiente

    personas_visibles = renderizar_barra_superior(db, usuario_actual)

    politica = PoliticaAccesoPersonas.desde_entorno()
    politica_capacidades = PoliticaCapacidades()

    paginas_con_persona = {
        clave for clave in PAGINAS_POR_CLAVE
        if requiere_persona_para_pagina(clave)
    }
    pagina_actual = st.session_state.get("pagina", "resumen")
    capacidad = capacidad_requerida_para_pagina(pagina_actual)
    if capacidad is not None:
        try:
            politica_capacidades.exigir(identidad, capacidad)
        except PermissionError as exc:
            componentes.nota_contextual(str(exc), "error")
            return

    if pagina_actual in paginas_con_persona:
        persona_id = st.session_state.get("persona_id")
        if persona_id is None:
            if not personas:
                # El estado inicial se presenta debajo, con un camino claro
                # para crear la primera persona; no es una denegación.
                pass
            elif not personas_visibles:
                componentes.nota_contextual(
                    "No hay una persona autorizada para esta pantalla.",
                    "error",
                )
                return
            else:
                componentes.estado_vacio(
                    icono="👤",
                    titulo="Elegí una persona para continuar",
                    texto=(
                        "Usá el selector de persona del encabezado para indicar "
                        "qué información financiera querés consultar."
                    ),
                )
                return
        else:
            try:
                ServicioContextoSesionSeguridad(
                    proveedor_identidad,
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
    elif pagina == "usuarios":
        render_usuarios(db, usuario_actual)
    elif not personas_visibles and pagina in paginas_con_persona:
        capacidad_personas = capacidad_requerida_para_pagina("personas")
        puede_crear_personas = (
            capacidad_personas is not None
            and politica_capacidades.puede(identidad, capacidad_personas)
        )
        componentes.estado_vacio(
            icono="🌱",
            titulo="Todavía no hay personas cargadas",
            texto=(
                "Creá la primera persona para empezar a registrar préstamos."
                if puede_crear_personas
                else "Pedile a un administrador que cree la primera persona."
            ),
        )
        if puede_crear_personas and st.button(
            "Crear primera persona",
            use_container_width=True,
            key="ir_a_crear_primera_persona",
        ):
            # Se aplica antes de volver a crear el widget de navegación.
            st.session_state["pagina_pendiente"] = "personas"
            st.rerun()
        return
    elif pagina == "mi_espacio":
        persona_id_propia = usuario_actual.persona_id
        if persona_id_propia is None:
            componentes.estado_vacio(
                icono="👤",
                titulo="Tu cuenta todavía no está vinculada a una persona",
                texto=(
                    "Pedile a un administrador que vincule tu cuenta con tu persona "
                    "desde Usuarios. Mi espacio no toma datos de otra persona seleccionada."
                ),
            )
            return
        if not politica.puede_consultar(persona_id_propia):
            componentes.nota_contextual(
                "No hay una persona autorizada para esta pantalla.",
                "error",
            )
            return
        try:
            ServicioContextoSesionSeguridad(
                proveedor_identidad,
                politica,
            ).construir(
                actor_declarado=operador_actual(),
                persona_id=persona_id_propia,
            )
        except AccesoPersonaDenegado:
            componentes.nota_contextual(
                "No hay una persona autorizada para esta pantalla.",
                "error",
            )
            return
        render_mi_espacio(db, persona_id_propia)
    elif pagina == "planificar":
        render_planificar(db, st.session_state["persona_id"])
    elif pagina == "escenarios":
        render_escenarios(db, st.session_state["persona_id"])
    elif pagina == "rendimiento":
        render_rendimiento(db, st.session_state["persona_id"])
    elif pagina == "reportes":
        render_reportes(db, st.session_state["persona_id"])
    elif pagina == "comparar":
        render_comparador(db, st.session_state["persona_id"])
    elif pagina == "prestamos":
        render_prestamos(db, st.session_state["persona_id"])
    elif pagina == "motor_v3":
        render_motor_v3(
            db,
            permitir_cambio_modo=politica_capacidades.puede(
                identidad,
                CAP_CONFIGURAR_MOTOR_V3,
            ),
        )
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