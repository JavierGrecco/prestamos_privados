"""Pruebas de autorización por capacidades."""

import pytest

from aplicacion.seguridad.capacidades import (
    CAP_OPERAR,
    CAP_VER_AUDITORIA,
    CAP_VER_MOTOR_V3,
    CAP_VER_PERSONAS,
    CAP_VER_PERSONA,
    PoliticaCapacidades,
)
from aplicacion.seguridad.identidad import IdentidadSesion


def identidad(*roles: str) -> IdentidadSesion:
    return IdentidadSesion(
        subject="test:usuario",
        nombre="Usuario Test",
        proveedor="TEST",
        autenticada=True,
        roles=frozenset(roles),
    )


def test_admin_tiene_todas_las_capacidades():
    politica = PoliticaCapacidades()

    todas = (
        CAP_VER_PERSONAS,
        CAP_VER_AUDITORIA,
        CAP_VER_MOTOR_V3,
        CAP_OPERAR,
        CAP_VER_PERSONA,
    )

    assert all(politica.puede(identidad("ADMIN"), cap) for cap in todas)


def test_operador_no_puede_configurar_motor_v3():
    politica = PoliticaCapacidades()

    assert politica.puede(identidad("OPERADOR"), CAP_VER_PERSONAS)
    assert politica.puede(identidad("OPERADOR"), CAP_VER_AUDITORIA)
    assert politica.puede(identidad("OPERADOR"), CAP_OPERAR)
    assert politica.puede(identidad("OPERADOR"), CAP_VER_PERSONA)
    assert not politica.puede(identidad("OPERADOR"), CAP_VER_MOTOR_V3)

    with pytest.raises(PermissionError, match="Motor"):
        politica.exigir(identidad("OPERADOR"), CAP_VER_MOTOR_V3)


def test_lectura_no_puede_operar_ni_ver_auditoria():
    politica = PoliticaCapacidades()

    assert politica.puede(identidad("LECTURA"), CAP_VER_PERSONAS)
    assert politica.puede(identidad("LECTURA"), CAP_VER_PERSONA)
    assert not politica.puede(identidad("LECTURA"), CAP_OPERAR)
    assert not politica.puede(identidad("LECTURA"), CAP_VER_AUDITORIA)


def test_roles_desconocidos_no_otorgan_capacidades():
    politica = PoliticaCapacidades()

    assert politica.capacidades_de(identidad("ROL_INEXISTENTE")) == frozenset()


def test_rol_local_invalido_es_rechazado():
    from aplicacion.seguridad.capacidades import rol_local_desde_entorno

    with pytest.raises(ValueError, match="Rol local desconocido"):
        rol_local_desde_entorno("NO_EXISTE")
