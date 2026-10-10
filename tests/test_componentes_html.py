"""Regresiones de seguridad para los componentes HTML compartidos."""

import pytest

from ui import componentes


def capturar_html(monkeypatch):
    salida = []
    monkeypatch.setattr(
        componentes.st,
        "markdown",
        lambda contenido, **kwargs: salida.append((contenido, kwargs)),
    )
    return salida



def test_fragmento_confiable_no_admite_construccion_publica():
    with pytest.raises(TypeError, match="solo se crean desde componentes seguros"):
        componentes.FragmentoHTMLConfiable("<strong>texto arbitrario</strong>")

    assert not hasattr(componentes, "fragmento_html_confiable")


def test_nota_contextual_escapa_mensaje_y_valida_tipo(monkeypatch):
    salida = capturar_html(monkeypatch)

    componentes.nota_contextual(
        '<img src=x onerror="alert(1)">',
        'warning" onclick="alert(2)',
    )

    html, opciones = salida[-1]
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html
    assert "<img src=x" not in html
    assert 'nota-warning" onclick=' not in html
    assert 'class="nota-contextual nota-info"' in html
    assert opciones["unsafe_allow_html"] is True


def test_tabla_escapa_texto_y_encabezados_por_defecto(monkeypatch):
    salida = capturar_html(monkeypatch)

    componentes.tabla(
        [{"texto": '<script>alert("x")</script>'}],
        [['<img src=x onerror="alert(1)">']],
    )

    html, _ = salida[-1]
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in html
    assert '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;' in html
    assert "<script>" not in html
    assert "<img src=x" not in html


def test_tabla_permite_badge_controlado_sin_confiar_en_su_texto(monkeypatch):
    salida = capturar_html(monkeypatch)

    componentes.tabla(
        [{"texto": "Estado"}],
        [[componentes.badge('<script>alert(1)</script>', "pagada")]],
    )

    html, _ = salida[-1]
    assert '<span class="badge estado-pagada">' in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>" not in html


def test_badge_no_acepta_tipo_css_arbitrario():
    badge = componentes.badge("Estado", 'ok" onclick="alert(1)')

    assert 'class="badge estado-info"' in badge
    assert "onclick" not in badge


def test_estado_vacio_escapa_titulo_y_descripcion(monkeypatch):
    salida = capturar_html(monkeypatch)

    componentes.estado_vacio(
        "👤",
        '<svg onload="alert(1)">',
        "<script>alert(1)</script>",
    )

    html, _ = salida[-1]
    assert "&lt;svg onload=&quot;alert(1)&quot;&gt;" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>" not in html
    assert "<svg" not in html
