"""Pruebas del servicio de auditoría global."""

from pathlib import Path

import pytest

from aplicacion.servicios.auditoria import FiltrosAuditoria, ServicioAuditoria
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios.auditoria import AuditoriaRepo
from infraestructura.repositorios.base import nuevo_correlacion_id


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "auditoria.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        correlacion = nuevo_correlacion_id()
        AuditoriaRepo(db).registrar(
            usuario="admin",
            operacion="PRESTAMO_CREADO",
            entidad="PRESTAMO",
            entidad_id=7,
            correlacion_id=correlacion,
            datos_nuevos={"capital": "1000.00"},
            motivo="Prueba",
        )
        AuditoriaRepo(db).registrar(
            usuario="admin",
            operacion="PRESTAMO_ACTIVADO",
            entidad="PRESTAMO",
            entidad_id=7,
            correlacion_id=correlacion,
            datos_anteriores={"estado": "BORRADOR"},
            datos_nuevos={"estado": "ACTIVO"},
            motivo="Activación",
        )
        yield db


def test_listar_filtra_por_usuario_operacion_y_entidad(db):
    servicio = ServicioAuditoria(db)

    entradas = servicio.listar(
        FiltrosAuditoria(
            usuario="admin",
            operacion="PRESTAMO_CREADO",
            entidad="PRESTAMO",
        )
    )

    assert len(entradas) == 1
    assert entradas[0].entidad_id == 7
    assert entradas[0].operacion == "PRESTAMO_CREADO"


def test_por_correlacion_reconstruye_operacion(db):
    servicio = ServicioAuditoria(db)
    entradas = servicio.listar()
    correlacion = entradas[0].correlacion_id

    completas = servicio.por_correlacion(correlacion)

    assert len(completas) == 2
    assert [x.operacion for x in completas] == [
        "PRESTAMO_CREADO",
        "PRESTAMO_ACTIVADO",
    ]


def test_limite_invalido_es_rechazado(db):
    with pytest.raises(ValueError, match="positivo"):
        ServicioAuditoria(db).listar(FiltrosAuditoria(limite=0))
