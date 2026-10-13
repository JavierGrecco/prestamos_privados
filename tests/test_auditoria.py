"""Pruebas del servicio de auditoría global."""

from pathlib import Path

import pytest

from aplicacion.servicios.auditoria import FiltrosAuditoria
from aplicacion.servicios.auditoria import ServicioAuditoria
from aplicacion.puertos.auditoria import EventoAuditoria
from infraestructura.composicion.pagos import crear_servicio_auditoria
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
    servicio = crear_servicio_auditoria(db)

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
    assert isinstance(entradas[0], EventoAuditoria)
    assert [x.operacion for x in servicio.operaciones()] == sorted(servicio.operaciones())
    assert "PRESTAMO" in servicio.entidades()


def test_por_correlacion_reconstruye_operacion(db):
    servicio = crear_servicio_auditoria(db)
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
        crear_servicio_auditoria(db).listar(FiltrosAuditoria(limite=0))


def test_auditoria_es_inmutable(db):
    repo = AuditoriaRepo(db)
    entradas = repo.listar()
    entrada_id = entradas[0].id

    with pytest.raises(Exception, match="inmutable"):
        db.ejecutar(
            "UPDATE auditoria SET motivo = ? WHERE id = ?",
            ("alterado", entrada_id),
        )

    with pytest.raises(Exception, match="no se elimina"):
        db.ejecutar(
            "DELETE FROM auditoria WHERE id = ?",
            (entrada_id,),
        )


def test_servicio_auditoria_se_puede_probar_sin_sqlite():
    evento = EventoAuditoria(
        id=41,
        fecha="2026-10-13T10:00:00",
        usuario="operador",
        operacion="MODO_CAMBIADO",
        entidad="CONFIGURACION",
        entidad_id=1,
        correlacion_id="corr-41",
    )

    class ConsultaFalsa:
        def __init__(self):
            self.filtros = None

        def listar(self, *, limite=200, usuario=None, operacion=None, entidad=None):
            self.filtros = (limite, usuario, operacion, entidad)
            return [evento]

        def operaciones(self, *, limite=100):
            return ["MODO_CAMBIADO"]

        def entidades(self, *, limite=100):
            return ["CONFIGURACION"]

        def por_correlacion(self, correlacion_id):
            return [evento] if correlacion_id == "corr-41" else []

    consulta = ConsultaFalsa()
    servicio = ServicioAuditoria(consulta=consulta)

    resultado = servicio.listar(
        FiltrosAuditoria(usuario="operador", operacion="MODO_CAMBIADO", limite=10)
    )

    assert resultado == [evento]
    assert consulta.filtros == (10, "operador", "MODO_CAMBIADO", None)
    assert servicio.operaciones() == ["MODO_CAMBIADO"]
    assert servicio.entidades() == ["CONFIGURACION"]
    assert servicio.por_correlacion("corr-41") == [evento]
