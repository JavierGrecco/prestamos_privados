"""Contrato visual del tema oscuro y los estilos adaptativos."""

from inspect import signature
from pathlib import Path
import tomllib

from ui.estilos import PALETAS, _construir_variables, _leer_css, aplicar_estilos


def test_tema_oscuro_es_el_predeterminado_y_fallback():
    assert signature(aplicar_estilos).parameters["tema"].default == "oscuro"
    assert set(PALETAS["oscuro"]) == set(PALETAS["claro"])
    assert set(PALETAS["oscuro"]) == set(PALETAS["intermedio"])


def test_controles_nativos_siguen_el_tema_seleccionado():
    assert PALETAS["oscuro"]["native_color_scheme"] == "dark"
    assert PALETAS["oscuro"]["date_icon_filter"] == "invert(1)"
    assert PALETAS["claro"]["native_color_scheme"] == "light"
    assert PALETAS["claro"]["date_icon_filter"] == "none"
    assert PALETAS["intermedio"]["native_color_scheme"] == "light"
    assert PALETAS["intermedio"]["date_icon_filter"] == "none"

    variables = _construir_variables(PALETAS["oscuro"])
    assert "--native-color-scheme: dark;" in variables
    assert "--date-icon-filter: invert(1);" in variables


def test_css_no_fuerza_dark_en_los_temas_alternativos():
    css = _leer_css()
    assert "color-scheme: var(--native-color-scheme)" in css
    assert "color-scheme: var(--native-color-scheme) !important;" in css
    assert "color-scheme: dark" not in css
    assert "max-width: 1480px" in css
    assert "section[data-testid=\"stSidebar\"]" in css


def test_configuracion_de_streamlit_conserva_dark_y_toolbar_minimal():
    raiz = Path(__file__).resolve().parents[1]
    config = tomllib.loads((raiz / ".streamlit" / "config.toml").read_text("utf-8"))

    assert config["theme"]["base"] == "dark"
    assert config["theme"]["backgroundColor"] == PALETAS["oscuro"]["bg"]
    assert config["client"]["toolbarMode"] == "minimal"
