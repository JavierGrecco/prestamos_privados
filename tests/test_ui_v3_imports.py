"""Smoke tests de los módulos UI de la integración V3."""

from pathlib import Path


def test_modulos_ui_v3_importan():
    import ui.pagina_motor_v3  # noqa: F401
    import ui.pagina_registrar_pago  # noqa: F401
    import ui.pagina_analisis  # noqa: F401
    import ui.preview_pago_v3  # noqa: F401
    import ui.pagina_operacion  # noqa: F401
    import ui.pagina_detalle_financiero  # noqa: F401


def test_renderer_preview_v3_es_solo_presentacion():
    path = Path(__file__).resolve().parents[1] / "ui" / "preview_pago_v3.py"
    source = path.read_text(encoding="utf-8")

    assert "ServicioPreviewPagoV3" not in source
    assert "ServicioPreviewPago" not in source
    assert "def renderizar_preview_pago_v3(preview: PreviewPagoV3)" in source


def test_fallo_preview_v3_solo_bloquea_modo_v3():
    path = Path(__file__).resolve().parents[1] / "ui" / "pagina_registrar_pago.py"
    source = path.read_text(encoding="utf-8")

    assert "if modo is ModoMotorPagoV3.V3 and not v3_preview_ok:" in source
    assert "if modo is not ModoMotorPagoV3.LEGACY and not v3_preview_ok:" not in source
