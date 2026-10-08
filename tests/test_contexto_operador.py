"""Pruebas del contexto de operador declarado."""

from ui.contexto_operador import operador_por_defecto


def test_operador_por_defecto_usa_admin_si_no_hay_configuracion(monkeypatch):
    monkeypatch.delenv("PRESTAMOS_OPERADOR", raising=False)
    assert operador_por_defecto() == "admin"


def test_operador_por_defecto_respeta_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("PRESTAMOS_OPERADOR", "operador-ci")
    assert operador_por_defecto() == "operador-ci"
