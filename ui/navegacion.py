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
    "prestamos": "Préstamos",
    "motor_v3": "Motor V3",
    "analisis": "Análisis",
    "pagos": "Pagos",
    "operacion": "Operación",
    "detalle_financiero": "Detalle financiero",
    "personas": "Personas",
}


def renderizar_navegacion() -> str:
    """
    Renderiza el selector de página y devuelve la página activa.
    """
    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "resumen"

    # El segmented_control usa la misma key que la variable, así
    # no hay que sincronizar nada.
    st.segmented_control(
        "Página",
        options=list(PAGINAS.keys()),
        format_func=lambda x: PAGINAS[x],
        default=st.session_state["pagina"],
        label_visibility="collapsed",
        key="pagina",
    )

    return st.session_state["pagina"]