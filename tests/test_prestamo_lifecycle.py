"""Pruebas del ciclo de vida de préstamos."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.servicios import (
    ErrorDatosInvalidos,
    ErrorEstadoInvalido,
    ServicioPrestamos,
)
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import AuditoriaRepo, PersonaRepo, PrestamoRepo


def crear_prestamo(db):
    personas = PersonaRepo(db)
    deudor = personas.crear(nombre="Deudor", apellido="Prueba")
    inversor = personas.crear(nombre="Inversor", apellido="Prueba")
    return ServicioPrestamos(db).crear_completo(
        deudor_id=deudor,
        capital=Decimal("100000.00"),
        plazo_meses=3,
        tasa_anual=Decimal("0.24"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[{"persona_id": inversor, "monto": Decimal("100000.00")}],
        usuario="test",
    )


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "lifecycle.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield db


def test_transicion_activo_en_mora_y_retorno_a_activo(db):
    prestamo_id = crear_prestamo(db)
    servicio = ServicioPrestamos(db)

    servicio.cambiar_estado(
        prestamo_id, "EN_MORA", usuario="operador", motivo="Vencimiento impago"
    )
    assert servicio.prestamos.obtener(prestamo_id).estado == "EN_MORA"

    servicio.cambiar_estado(
        prestamo_id, "ACTIVO", usuario="operador", motivo="Regularización"
    )
    assert servicio.prestamos.obtener(prestamo_id).estado == "ACTIVO"


def test_transicion_ilegal_es_rechazada(db):
    prestamo_id = crear_prestamo(db)
    servicio = ServicioPrestamos(db)

    with pytest.raises(ErrorEstadoInvalido):
        servicio.cambiar_estado(
            prestamo_id, "REFINANCIADO", usuario="operador"
        )

    assert servicio.prestamos.obtener(prestamo_id).estado == "ACTIVO"


def test_cancelar_exige_motivo_y_deja_estado_terminal(db):
    prestamo_id = crear_prestamo(db)
    servicio = ServicioPrestamos(db)

    with pytest.raises(ErrorDatosInvalidos):
        servicio.cambiar_estado(
            prestamo_id, "CANCELADO", usuario="operador"
        )

    servicio.cambiar_estado(
        prestamo_id,
        "CANCELADO",
        usuario="operador",
        motivo="Cancelación acordada con el deudor",
    )

    assert servicio.prestamos.obtener(prestamo_id).estado == "CANCELADO"
    assert servicio.opciones_de_estado(prestamo_id) == ()


def test_finalizar_rechaza_cuotas_pendientes(db):
    prestamo_id = crear_prestamo(db)
    servicio = ServicioPrestamos(db)

    assert servicio.puede_finalizar(prestamo_id) is False

    with pytest.raises(ErrorEstadoInvalido):
        servicio.cambiar_estado(
            prestamo_id, "FINALIZADO", usuario="operador"
        )

    assert servicio.prestamos.obtener(prestamo_id).estado == "ACTIVO"


def test_finalizar_cuando_todas_las_cuotas_estan_cerradas(db):
    prestamo_id = crear_prestamo(db)
    servicio = ServicioPrestamos(db)
    repo = PrestamoRepo(db)
    version_id = repo.version_activa(prestamo_id)

    for cuota in repo.cuotas(version_id):
        repo.actualizar_cuota(
            cuota.id,
            estado="PAGADA",
            interes_pendiente=Decimal("0"),
            capital_pendiente=Decimal("0"),
            mora_pendiente=Decimal("0"),
            fue_mora=False,
            tuvo_pago_parcial=False,
        )

    assert servicio.puede_finalizar(prestamo_id) is True

    servicio.cambiar_estado(
        prestamo_id,
        "FINALIZADO",
        usuario="operador",
        motivo="Todas las cuotas fueron canceladas",
    )

    assert servicio.prestamos.obtener(prestamo_id).estado == "FINALIZADO"


def test_cambio_de_estado_queda_auditado(db):
    prestamo_id = crear_prestamo(db)
    servicio = ServicioPrestamos(db)

    servicio.cambiar_estado(
        prestamo_id, "EN_MORA", usuario="operador", motivo="Atraso"
    )

    auditoria = AuditoriaRepo(db).por_entidad("PRESTAMO", prestamo_id)
    entrada = next(
        e for e in auditoria if e.operacion == "PRESTAMO_ESTADO_CAMBIADO"
    )

    assert entrada.usuario == "operador"
    assert "ACTIVO" in (entrada.datos_anteriores or "")
    assert "EN_MORA" in (entrada.datos_nuevos or "")
    assert entrada.motivo == "Atraso"
    assert entrada.correlacion_id
