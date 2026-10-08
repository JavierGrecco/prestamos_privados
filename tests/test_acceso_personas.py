"""Pruebas de la frontera de autorización por persona."""

import pytest

from aplicacion.seguridad.acceso_personas import (
    AccesoPersonaDenegado,
    PoliticaAccesoPersonas,
)


def test_modo_local_no_confunde_seleccion_con_autenticacion():
    politica = PoliticaAccesoPersonas(personas_permitidas=set())

    contexto = politica.autorizar(
        7,
        actor_declarado="operador-local",
    )

    assert contexto.autorizado
    assert contexto.modo == "LOCAL_SIN_AUTENTICACION"
    assert not contexto.autenticacion_real
    assert contexto.actor_declarado == "operador-local"


def test_allowlist_deniega_persona_fuera_del_alcance():
    politica = PoliticaAccesoPersonas(personas_permitidas={1, 2})

    assert politica.puede_consultar(1)
    assert politica.puede_consultar(2)
    assert not politica.puede_consultar(3)

    with pytest.raises(
        AccesoPersonaDenegado,
        match="no está autorizada",
    ):
        politica.autorizar(3, actor_declarado="operador")


def test_allowlist_acepta_persona_autorizada():
    politica = PoliticaAccesoPersonas(personas_permitidas={4})

    contexto = politica.autorizar(
        4,
        actor_declarado="operador",
    )

    assert contexto.modo == "ALLOWLIST"
    assert contexto.autorizado
    assert contexto.persona_id == 4


def test_allowlist_desde_entorno(monkeypatch):
    monkeypatch.setenv(
        "PRESTAMOS_PERSONAS_PERMITIDAS",
        "2, 5, 8",
    )

    politica = PoliticaAccesoPersonas.desde_entorno()

    assert politica.personas_permitidas == frozenset({2, 5, 8})
    assert politica.modo == "ALLOWLIST"


def test_allowlist_entorno_invalido():
    with pytest.raises(
        ValueError,
        match="IDs separados por comas",
    ):
        PoliticaAccesoPersonas({"abc"})


def test_ids_no_positivos_no_se_autorizan():
    politica = PoliticaAccesoPersonas(personas_permitidas={1})

    assert not politica.puede_consultar(0)
    assert not politica.puede_consultar(-1)
