"""Regresiones del tema CSS y del esquema de color nativo."""

from ui import estilos


def _luminancia(hex_color: str) -> float:
    """Calcula la luminancia relativa sRGB de un color hexadecimal."""
    canales = []
    for inicio in (1, 3, 5):
        canal = int(hex_color[inicio:inicio + 2], 16) / 255
        canales.append(
            canal / 12.92
            if canal <= 0.04045
            else ((canal + 0.055) / 1.055) ** 2.4
        )
    return (
        0.2126 * canales[0]
        + 0.7152 * canales[1]
        + 0.0722 * canales[2]
    )


def _contraste(color_a: str, color_b: str) -> float:
    luminancia_a = _luminancia(color_a)
    luminancia_b = _luminancia(color_b)
    clara, oscura = sorted((luminancia_a, luminancia_b), reverse=True)
    return (clara + 0.05) / (oscura + 0.05)


PARES_TEXTO_FONDO = (
    ("text", "bg"),
    ("text", "bg_card"),
    ("text", "bg_card_hover"),
    ("text", "bg_seg"),
    ("text", "bg_seg_hover"),
    ("text", "bg_table_head"),
    ("text", "bg_calendar"),
    ("text", "bg_calendar_hover"),
    ("text_muted", "bg"),
    ("text_muted", "bg_card"),
    ("text_muted", "bg_table_head"),
    ("text_subtle", "bg"),
    ("text_subtle", "bg_card"),
    ("text_subtle", "bg_table_head"),
    ("text_button", "bg_button"),
    ("text_button", "bg_button_hover"),
    ("text_button", "bg_button_active"),
    ("primary", "bg"),
    ("primary", "bg_card"),
    ("primary", "bg_seg"),
    ("primary", "bg_card_hover"),
    ("primary", "bg_table_head"),
    ("primary_text", "primary"),
    ("green", "green_soft"),
    ("red", "red_soft"),
    ("amber", "amber_soft"),
    ("neutral", "neutral_soft"),
)


def test_combinaciones_de_texto_cumplen_contraste_wcag_aa_en_todos_los_temas():
    for tema, paleta in estilos.PALETAS.items():
        for clave_texto, clave_fondo in PARES_TEXTO_FONDO:
            ratio = _contraste(paleta[clave_texto], paleta[clave_fondo])
            assert ratio >= 4.5, (
                f"El tema {tema} no alcanza WCAG AA para texto normal: "
                f"{clave_texto} sobre {clave_fondo} = {ratio:.2f}:1 "
                "(mínimo 4.5:1)."
            )



def test_tema_oscuro_es_el_predeterminado(monkeypatch):
    salida = []
    monkeypatch.setattr(
        estilos.st,
        "markdown",
        lambda contenido, **kwargs: salida.append(contenido),
    )

    estilos.aplicar_estilos()

    assert salida
    assert "color-scheme: dark;" in salida[-1]
    assert "__COLOR_SCHEME__" not in salida[-1]
    assert "--bg: #0F172A;" in salida[-1]
    assert "--calendar-icon-filter: invert(1);" in salida[-1]


def test_esquema_nativo_sigue_el_tema_seleccionado(monkeypatch):
    salida = []
    monkeypatch.setattr(
        estilos.st,
        "markdown",
        lambda contenido, **kwargs: salida.append(contenido),
    )

    for tema in ("claro", "intermedio", "oscuro"):
        estilos.aplicar_estilos(tema)
        esperado = "dark" if tema == "oscuro" else "light"
        assert f"color-scheme: {esperado};" in salida[-1]
        esperado_filtro_icono = "invert(1)" if tema == "oscuro" else "none"
        assert f"--calendar-icon-filter: {esperado_filtro_icono};" in salida[-1]
        assert "filter: var(--calendar-icon-filter) !important;" in salida[-1]
        assert "filter: invert(1) !important;" not in salida[-1]
        assert "__VARIABLES__" not in salida[-1]
        assert "__COLOR_SCHEME__" not in salida[-1]


def test_tema_desconocido_falla_a_oscuro_de_forma_predecible(monkeypatch):
    salida = []
    monkeypatch.setattr(
        estilos.st,
        "markdown",
        lambda contenido, **kwargs: salida.append(contenido),
    )

    estilos.aplicar_estilos("tema-inexistente")

    assert "color-scheme: dark;" in salida[-1]
    assert "--bg: #0F172A;" in salida[-1]
