"""Smoke tests de los módulos UI de la integración V3."""


def test_modulos_ui_v3_importan():
    import ui.pagina_motor_v3  # noqa: F401
    import ui.pagina_registrar_pago  # noqa: F401
    import ui.pagina_analisis  # noqa: F401
    import ui.preview_pago_v3  # noqa: F401
    import ui.pagina_operacion  # noqa: F401
    import ui.pagina_detalle_financiero  # noqa: F401
