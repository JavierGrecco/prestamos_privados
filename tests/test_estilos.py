"""Regresiones del tema CSS y del esquema de color nativo."""

from ui import estilos


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
