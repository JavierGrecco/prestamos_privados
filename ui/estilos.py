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
    "bg_sidebar": "#F7F8FB",
    "bg_sidebar_hover": "#E9EDF4",
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
    "native_color_scheme": "light",
    "date_icon_filter": "none",
    "text": "#1F2937",
    "text_muted": "#6B7280",
    "text_subtle": "#9CA3AF",
    "text_button": "#1F2937",
    "border": "#E5E1DA",
    "border_strong": "#C9C4BA",
    "primary": "#0284C7",
    "primary_text": "#FFFFFF",
    "green": "#15803D",
    "green_soft": "#DCFCE7",
    "red": "#B91C1C",
    "red_soft": "#FEE2E2",
    "amber": "#D97706",
    "amber_soft": "#FEF3C7",
    "neutral": "#6B7280",
    "neutral_soft": "#E5E7EB",
}

PALETA_INTERMEDIA = {
    "bg": "#DED9CF",
    "bg_sidebar": "#D8D2C4",
    "bg_sidebar_hover": "#C9C0AF",
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
    "native_color_scheme": "light",
    "date_icon_filter": "none",
    "text": "#25231F",
    "text_muted": "#5C5749",
    "text_subtle": "#89836F",
    "text_button": "#25231F",
    "border": "#C9C2B3",
    "border_strong": "#ADA594",
    "primary": "#0369A1",
    "primary_text": "#FFFFFF",
    "green": "#166534",
    "green_soft": "#D3DEC4",
    "red": "#991B1B",
    "red_soft": "#E5CFC4",
    "amber": "#B45309",
    "amber_soft": "#E5D8C4",
    "neutral": "#57534E",
    "neutral_soft": "#CFC9BC",
}

PALETA_OSCURA = {
    "bg": "#0B1220",
    "bg_sidebar": "#080F1B",
    "bg_sidebar_hover": "#1B2A41",
    "bg_card": "#111B2E",
    "bg_card_hover": "#1B2A41",
    "bg_seg": "#111B2E",
    "bg_seg_hover": "#1B2A41",
    "bg_button": "#111B2E",
    "bg_button_hover": "#1B2A41",
    "bg_button_active": "#263854",
    "bg_table_head": "#1B2A41",
    "bg_calendar": "#111B2E",
    "bg_calendar_hover": "#1B2A41",
    "native_color_scheme": "dark",
    "date_icon_filter": "invert(1)",
    "text": "#F1F5F9",
    "text_muted": "#94A3B8",
    "text_subtle": "#7788A3",
    "text_button": "#F1F5F9",
    "border": "#263449",
    "border_strong": "#3A4B63",
    "primary": "#38BDF8",
    "primary_text": "#08111F",
    "green": "#4ADE80",
    "green_soft": "#14532D",
    "red": "#F87171",
    "red_soft": "#7F1D1D",
    "amber": "#FBBF24",
    "amber_soft": "#78350F",
    "neutral": "#94A3B8",
    "neutral_soft": "#263449",
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
    Inyecta el CSS con las variables del tema elegido.

    Parámetros:
        tema: "claro", "intermedio" o "oscuro".
    """
    paleta = PALETAS.get(tema, PALETA_OSCURA)
    variables = _construir_variables(paleta)
    css = _leer_css()
    css_final = css.replace("__VARIABLES__", variables)
    st.markdown(f"<style>{css_final}</style>", unsafe_allow_html=True)