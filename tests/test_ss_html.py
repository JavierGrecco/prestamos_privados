"""Regresiones para la pantalla principal heredada."""

from decimal import Decimal
from types import SimpleNamespace

from ui import componentes, ss


class ColumnaFalsa:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def test_renderer_heredado_escapa_nombre_y_detalles(monkeypatch):
    salida = []
    persona = SimpleNamespace(nombre='<img src=x onerror="alert(1)">')
    metricas = SimpleNamespace(
        veredicto="CRECIENDO",
        mensaje_principal="creciendo",
        efecto_neto=Decimal("100.00"),
        capital_invertido=Decimal("1000.00"),
        capital_adeudado=Decimal("500.00"),
        detalle_inversion='<script>alert("inversion")</script>',
        detalle_deuda='<svg onload="alert(2)">deuda</svg>',
    )

    class PersonaRepoFalsa:
        def __init__(self, db):
            pass

        def obtener(self, persona_id):
            return persona

    monkeypatch.setattr(ss, "PersonaRepo", PersonaRepoFalsa)
    monkeypatch.setattr(ss, "calcular_metricas", lambda db, persona_id: metricas)
    monkeypatch.setattr(ss, "color_para_veredicto", lambda veredicto: "color-verde")
    monkeypatch.setattr(ss, "emoji_para_veredicto", lambda veredicto: "📈")
    monkeypatch.setattr(componentes, "render_html", lambda contenido: salida.append(contenido))
    monkeypatch.setattr(componentes, "renderizar_nota_pendiente", lambda: None)
    monkeypatch.setattr(ss.st, "columns", lambda *args, **kwargs: [ColumnaFalsa() for _ in range(4)])
    monkeypatch.setattr(ss.st, "button", lambda *args, **kwargs: False)

    ss.render(object(), 1)

    html = "\n".join(salida)
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html
    assert "&lt;script&gt;alert(&quot;inversion&quot;)&lt;/script&gt;" in html
    assert "&lt;svg onload=&quot;alert(2)&quot;&gt;deuda&lt;/svg&gt;" in html
    assert "<img src=x" not in html
    assert "<script>" not in html
    assert "<svg" not in html
