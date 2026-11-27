"""Regresiones de accesibilidad para la hoja de estilos de Streamlit."""

from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
CSS_COMPONENTES = RAIZ / "ui" / "estilos_componentes.css"
ESTILOS_PY = RAIZ / "ui" / "estilos.py"


def _css_componentes() -> str:
    return CSS_COMPONENTES.read_text(encoding="utf-8")


def test_accessibility_rules_are_loaded_after_control_styles() -> None:
    estilos = ESTILOS_PY.read_text(encoding="utf-8")
    inicio = estilos.index("ARCHIVOS_CSS = [")
    fin = estilos.index("]", inicio)
    archivos = estilos[inicio:fin]

    assert archivos.index('"estilos_controles.css"') < archivos.index(
        '"estilos_componentes.css"'
    )
    assert ":focus-visible" in _css_componentes()


def test_interactive_elements_have_a_visible_keyboard_focus_rule() -> None:
    css = _css_componentes()

    assert ":focus-visible" in css
    assert "outline-offset: 2px" in css
    assert "outline: 3px solid var(--primary) !important" in css


def test_global_styles_respect_reduced_motion_preferences() -> None:
    css = _css_componentes()

    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "transition-duration: 0.01ms" in css
    assert "animation-duration: 0.01ms" in css


def test_global_styles_support_forced_colors_mode() -> None:
    css = _css_componentes()

    assert "@media (forced-colors: active)" in css
    assert "outline-color: Highlight" in css
    assert "border: 1px solid CanvasText" in css
