"""
Estilos de la app.

Lee los 3 archivos CSS (base, controles, componentes), reemplaza
las variables según el tema activo, y los inyecta en Streamlit.

Separar el CSS en 3 archivos tiene ventajas:
  1. Cada archivo se edita con syntax highlighting correcto.
  2. No hay que escapar llaves { } como en los f-strings.
  3. Es más fácil ubicar y modificar una regla específica.
"""
from pathlib import Path

import streamlit as st


# ============================================================
# Paletas
# ============================================================

PALETA_CLARA = {
    "bg": "#F2F1EE",
    "bg_card": "#FBFAF7",
    "bg_card_hover": "#F0EEE9",
    "bg_seg": "#E8E5DE",
    "bg_seg_hover": "#DDD9CF",
    "bg_button": "#FFFFFF",
    "bg_button_hover": "#F0EEE9",
    "bg_button_active": "#E5E1DA",
    "bg_table_head": "#F0EEE9",
    "bg_calendar": "#FFFFFF",
    "bg_calendar_hover": "#F0EEE9",
    "calendar_icon_filter": "none",
    "text": "#1F2937",
    "text_muted": "#5B6472",
    "text_subtle": "#626B78",
    "text_button": "#1F2937",
    "border": "#E5E1DA",
    "border_strong": "#C9C4BA",
    "primary": "#0369A1",
    "primary_text": "#FFFFFF",
    "green": "#15803D",
    "green_soft": "#DCFCE7",
    "red": "#B91C1C",
    "red_soft": "#FEE2E2",
    "amber": "#78350F",
    "amber_soft": "#FEF3C7",
    "neutral": "#4B5563",
    "neutral_soft": "#E5E7EB",
}

PALETA_INTERMEDIA = {
    "bg": "#DED9CF",
    "bg_card": "#EBE6DB",
    "bg_card_hover": "#E2DCD1",
    "bg_seg": "#D3CCBF",
    "bg_seg_hover": "#C9C0AF",
    "bg_button": "#EBE6DB",
    "bg_button_hover": "#E2DCD1",
    "bg_button_active": "#D8D2C4",
    "bg_table_head": "#D8D2C4",
    "bg_calendar": "#EBE6DB",
    "bg_calendar_hover": "#E2DCD1",
    "calendar_icon_filter": "none",
    "text": "#25231F",
    "text_muted": "#514D45",
    "text_subtle": "#57534E",
    "text_button": "#25231F",
    "border": "#C9C2B3",
    "border_strong": "#ADA594",
    "primary": "#075985",
    "primary_text": "#FFFFFF",
    "green": "#166534",
    "green_soft": "#D3DEC4",
    "red": "#991B1B",
    "red_soft": "#E5CFC4",
    "amber": "#78350F",
    "amber_soft": "#E5D8C4",
    "neutral": "#57534E",
    "neutral_soft": "#CFC9BC",
}

PALETA_OSCURA = {
    "bg": "#0F172A",
    "bg_card": "#1E293B",
    "bg_card_hover": "#334155",
    "bg_seg": "#1E293B",
    "bg_seg_hover": "#334155",
    "bg_button": "#1E293B",
    "bg_button_hover": "#334155",
    "bg_button_active": "#475569",
    "bg_table_head": "#334155",
    "bg_calendar": "#1E293B",
    "bg_calendar_hover": "#334155",
    "calendar_icon_filter": "invert(1)",
    "text": "#F1F5F9",
    "text_muted": "#A8B5C7",
    "text_subtle": "#B6C2D2",
    "text_button": "#F1F5F9",
    "border": "#334155",
    "border_strong": "#475569",
    "primary": "#38BDF8",
    "primary_text": "#0F172A",
    "green": "#4ADE80",
    "green_soft": "#14532D",
    "red": "#FCA5A5",
    "red_soft": "#7F1D1D",
    "amber": "#FBBF24",
    "amber_soft": "#78350F",
    "neutral": "#CBD5E1",
    "neutral_soft": "#334155",
}

PALETAS = {
    "claro": PALETA_CLARA,
    "intermedio": PALETA_INTERMEDIA,
    "oscuro": PALETA_OSCURA,
}


# ============================================================
# Carga de CSS
# ============================================================

DIR_UI = Path(__file__).parent

ARCHIVOS_CSS = [
    "estilos_base.css",
    "estilos_controles.css",
    "estilos_componentes.css",
]


def _construir_variables(paleta: dict) -> str:
    """
    Construye el bloque de variables CSS a partir de una paleta.

    Convierte claves con guión bajo a guión medio:
        text_muted -> --text-muted: #6B7280;
    """
    return "\n".join(
        f"    --{clave.replace('_', '-')}: {valor};"
        for clave, valor in paleta.items()
    )


def _leer_css() -> str:
    """
    Lee y concatena los 3 archivos CSS.

    Devuelve el CSS completo con los 3 fragmentos unidos.
    """
    partes = []
    for nombre in ARCHIVOS_CSS:
        ruta = DIR_UI / nombre
        try:
            partes.append(ruta.read_text(encoding="utf-8"))
        except FileNotFoundError:
            partes.append(f"/* Falta: {nombre} */")
    return "\n".join(partes)


def aplicar_estilos(tema: str = "oscuro") -> None:
    """
    Inyecta el CSS y el esquema nativo coherente con el tema seleccionado.

    El tema oscuro es el predeterminado del producto. Los temas alternativos
    conservan un esquema nativo claro para inputs, fechas y desplegables.
    """
    tema_normalizado = tema if tema in PALETAS else "oscuro"
    paleta = PALETAS[tema_normalizado]
    variables = _construir_variables(paleta)
    esquema_color = "dark" if tema_normalizado == "oscuro" else "light"
    css = _leer_css()
    css_final = (
        css.replace("__VARIABLES__", variables)
        .replace("__COLOR_SCHEME__", esquema_color)
    )
    st.markdown(f"<style>{css_final}</style>", unsafe_allow_html=True)