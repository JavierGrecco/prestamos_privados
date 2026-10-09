"""
Barra de navegación entre páginas.

Usa un segmented_control horizontal en la parte superior, alineado
a la izquierda. La página actual se guarda en session_state.
"""
import streamlit as st


# ============================================================
# Definición de páginas
# ============================================================
PAGINAS = {
    "resumen": "Resumen",
    "planificar": "Planificar",
    "escenarios": "Escenarios",
    "rendimiento": "Rendimiento",
    "reportes": "Reportes",
    "comparar": "Comparar",
    "mi_espacio": "Mi espacio",
    "prestamos": "Préstamos",
    "motor_v3": "Motor V3",
    "analisis": "Análisis",
    "pagos": "Pagos",
    "operacion": "Operación",
    "detalle_financiero": "Detalle financiero",
    "personas": "Personas",
    "auditoria": "Auditoría",
    "usuarios": "Usuarios",
}


def renderizar_navegacion(paginas_permitidas: tuple[str, ...] | None = None) -> str:
    """
    Renderiza el selector de página y devuelve la página activa.
    """
    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "resumen"

    opciones = (
        PAGINAS
        if paginas_permitidas is None
        else {
            clave: etiqueta
            for clave, etiqueta in PAGINAS.items()
            if clave in paginas_permitidas
        }
    )
    if not opciones:
        raise ValueError("La sesión no tiene páginas disponibles.")
    if st.session_state["pagina"] not in opciones:
        # Resolver el cambio de rol antes de instanciar el widget.
        st.session_state["pagina"] = next(iter(opciones))

    # El segmented_control usa la misma key que la variable, así
    # no hay que sincronizar nada.
    st.segmented_control(
        "Página",
        options=list(opciones.keys()),
        format_func=lambda x: opciones[x],
        default=st.session_state["pagina"],
        label_visibility="collapsed",
        key="pagina",
    )

    return st.session_state["pagina"]