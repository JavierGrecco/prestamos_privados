"""Pruebas de identidad y contexto de sesión."""

import pytest

from aplicacion.seguridad.acceso_personas import (
    AccesoPersonaDenegado,
    PoliticaAccesoPersonas,
)
from aplicacion.seguridad.contexto_sesion import ServicioContextoSesionSeguridad
from aplicacion.seguridad.identidad import (
    IdentidadSesion,
    ProveedorIdentidadLocal,
    identidad_desde_proveedor,
)


class ProveedorFalso:
    def obtener_identidad(self) -> IdentidadSesion:
        return IdentidadSesion(
            subject="oidc:123",
            nombre="Usuario Real",
            proveedor="OIDC",
            autenticada=True,
        )


class ProveedorInvalido:
    def obtener_identidad(self):
        return {"subject": "123"}


def test_proveedor_local_deja_claro_que_no_autentica(monkeypatch):
    monkeypatch.setenv("PRESTAMOS_OPERADOR", "javier")

    identidad = ProveedorIdentidadLocal().obtener_identidad()

    assert identidad.subject == "local:javier"
    assert identidad.nombre == "javier"
    assert identidad.proveedor == "LOCAL"
    assert not identidad.autenticada


def test_proveedor_real_puede_ser_inyectado():
    identidad = identidad_desde_proveedor(ProveedorFalso())

    assert identidad.subject == "oidc:123"
    assert identidad.proveedor == "OIDC"
    assert identidad.autenticada


def test_proveedor_invalido_es_rechazado():
    with pytest.raises(TypeError, match="IdentidadSesion"):
        identidad_desde_proveedor(ProveedorInvalido())


def test_contexto_separa_identidad_actor_y_persona():
    contexto = ServicioContextoSesionSeguridad(
        ProveedorFalso(),
        PoliticaAccesoPersonas({10}),
    ).construir(
        actor_declarado="operador-auditoria",
        persona_id=10,
    )

    assert contexto.identidad.subject == "oidc:123"
    assert contexto.identidad.autenticada
    assert contexto.actor_declarado == "operador-auditoria"
    assert contexto.persona_id == 10
    assert contexto.acceso is not None
    assert contexto.acceso.autorizado


def test_contexto_deniega_persona_fuera_del_alcance():
    with pytest.raises(AccesoPersonaDenegado):
        ServicioContextoSesionSeguridad(
            ProveedorFalso(),
            PoliticaAccesoPersonas({10}),
        ).construir(
            actor_declarado="operador-auditoria",
            persona_id=11,
        )


def test_contexto_puede_existir_sin_persona_seleccionada():
    contexto = ServicioContextoSesionSeguridad(
        ProveedorFalso(),
        PoliticaAccesoPersonas({10}),
    ).construir(
        actor_declarado="operador-auditoria",
        persona_id=None,
    )

    assert contexto.persona_id is None
    assert contexto.acceso is None
    assert contexto.autenticada
