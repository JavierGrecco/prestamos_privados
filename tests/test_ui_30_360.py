"""Regresión del contrato de convención 30/360."""

from ui.pagina_alta_prestamo import CONVENCIONES_UI_A_DOMINIO


def test_ui_mapea_treinta_360_al_valor_persistido():
    assert CONVENCIONES_UI_A_DOMINIO["TREINTA_360"] == "30_360"
