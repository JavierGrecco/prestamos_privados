"""Regresiones para el HTML del historial de decisiones."""

from datetime import date
from decimal import Decimal

from ui import componentes, pagina_prestamos


def test_historial_escapa_textos_provenientes_de_datos(monkeypatch):
    renderizados = []
    monkeypatch.setattr(
        componentes,
        "render_html",
        lambda contenido: renderizados.append(contenido),
    )

    pagina_prestamos._renderizar_historial(
        [
            {
                "monto_impacto": Decimal("125.00"),
                "icono": '<img src=x onerror="alert(1)">',
                "fecha": date(2026, 10, 8),
                "titulo": '<script>alert("titulo")</script>',
                "descripcion": '<svg onload="alert(2)">detalle</svg>',
                "impacto": '<iframe src="javascript:alert(3)">',
            }
        ]
    )

    html = "\n".join(renderizados)
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html
    assert "&lt;script&gt;alert(&quot;titulo&quot;)&lt;/script&gt;" in html
    assert "&lt;svg onload=&quot;alert(2)&quot;&gt;detalle&lt;/svg&gt;" in html
    assert "&lt;iframe src=&quot;javascript:alert(3)&quot;&gt;" in html
    assert "<script>" not in html
    assert "<svg" not in html
    assert "<iframe" not in html
    assert "<img src=x" not in html
