"""Regresiones de accesibilidad para la hoja de estilos global de Streamlit."""

from pathlib import Path


CSS_BASE = Path(__file__).resolve().parents[1] / "ui" / "estilos_base.css"


def _css_base() -> str:
    return CSS_BASE.read_text(encoding="utf-8")


def test_interactive_elements_have_a_visible_keyboard_focus_rule() -> None:
    css = _css_base()

    assert ":focus-visible" in css
    assert "outline-offset: 2px" in css


def test_global_styles_respect_reduced_motion_preferences() -> None:
    css = _css_base()

    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "transition-duration: 0.01ms" in css
    assert "animation-duration: 0.01ms" in css


def test_global_styles_support_forced_colors_mode() -> None:
    css = _css_base()

    assert "@media (forced-colors: active)" in css
    assert "outline-color: Highlight" in css
    assert "border: 1px solid CanvasText" in css
