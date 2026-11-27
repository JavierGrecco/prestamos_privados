"""Pruebas del ensamblado explícito del servicio Legacy de pagos."""

import warnings
from uuid import UUID

import pytest

from aplicacion.servicios.pagos import ServicioPagos
from aplicacion.servicios.pagos_simulacion import ServicioPagosConSimulacion
from infraestructura import BaseDatos
from infraestructura.composicion.servicio_pagos_legacy import (
    crear_servicio_pagos_legacy,
)
from infraestructura.repositorios import (
    AuditoriaRepo,
    LedgerRepo,
    PagoRepo,
    ParticipacionRepo,
    PoliticaPagoRepo,
    PrestamoRepo,
    RecalculoRepo,
)


def test_fabrica_inyecta_todos_los_colaboradores_y_conserva_simulacion(tmp_path):
    with BaseDatos(tmp_path / "composicion-servicio-pagos.db") as db:
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            servicio = crear_servicio_pagos_legacy(db)

        assert isinstance(servicio, ServicioPagosConSimulacion)
        assert servicio.db is db
        assert isinstance(servicio.prestamos, PrestamoRepo)
        assert isinstance(servicio.pagos, PagoRepo)
        assert isinstance(servicio.participaciones, ParticipacionRepo)
        assert isinstance(servicio.ledger, LedgerRepo)
        assert isinstance(servicio.auditoria, AuditoriaRepo)
        assert isinstance(servicio.recalculos, RecalculoRepo)
        assert isinstance(servicio.politicas_pago, PoliticaPagoRepo)
        # Todos los repositorios deben usar esta misma BaseDatos. Así, las
        # escrituras que coordinan quedan dentro de una única transacción.
        repositorios = (
            servicio.prestamos,
            servicio.pagos,
            servicio.participaciones,
            servicio.ledger,
            servicio.auditoria,
            servicio.recalculos,
            servicio.politicas_pago,
        )
        assert all(repositorio.db is db for repositorio in repositorios), (
            "Todos los repositorios de pagos deben compartir la misma BaseDatos"
        )

        # El manejador debe usar tanto la misma unidad de trabajo como los
        # mismos repositorios que expone la fachada; no debe crear duplicados.
        manejador = servicio._manejador_registro_pago_legacy
        assert manejador.unidad_trabajo is db
        assert manejador.prestamos is servicio.prestamos
        assert manejador.pagos is servicio.pagos
        assert manejador.participaciones is servicio.participaciones
        assert manejador.ledger is servicio.ledger
        assert manejador.auditoria is servicio.auditoria
        assert manejador.recalculos is servicio.recalculos
        assert manejador.politicas_pago is servicio.politicas_pago


def test_fachada_rechaza_inyeccion_parcial(tmp_path):
    with BaseDatos(tmp_path / "composicion-parcial.db") as db:
        with pytest.raises(ValueError, match="inyección requiere todos"):
            ServicioPagos(db, prestamos=PrestamoRepo(db))

def test_constructor_historico_sigue_disponible_como_puente_temporal(tmp_path):
    """El puente se conserva expresamente hasta migrar los consumidores externos."""
    with BaseDatos(tmp_path / "compatibilidad-constructor.db") as db:
        with pytest.warns(
            DeprecationWarning,
            match="ServicioPagos\\(db\\) está obsoleto",
        ):
            servicio = ServicioPagos(db)

        assert servicio.db is db
        assert isinstance(servicio.prestamos, PrestamoRepo)
        assert isinstance(servicio.pagos, PagoRepo)
        assert isinstance(servicio.participaciones, ParticipacionRepo)
        assert isinstance(servicio.ledger, LedgerRepo)
        assert isinstance(servicio.auditoria, AuditoriaRepo)
        assert isinstance(servicio.recalculos, RecalculoRepo)
        assert isinstance(servicio.politicas_pago, PoliticaPagoRepo)



def test_fachada_acepta_unidad_de_trabajo_y_generador_por_contrato():
    """La aplicación recibe un puerto, no necesita BaseDatos para ensamblarse."""
    unidad_trabajo = object()
    generador = lambda: "correlacion-inyectada"
    servicio = ServicioPagos(
        unidad_trabajo,
        prestamos=object(),
        pagos=object(),
        participaciones=object(),
        ledger=object(),
        auditoria=object(),
        recalculos=object(),
        politicas_pago=object(),
        generador_correlacion=generador,
    )

    assert servicio.db is unidad_trabajo
    assert servicio._manejador_registro_pago_legacy.unidad_trabajo is unidad_trabajo
    assert (
        servicio._manejador_registro_pago_legacy._nuevo_correlacion_id()
        == "correlacion-inyectada"
    )


def test_generador_de_correlacion_predeterminado_sigue_produciendo_uuid_v4():
    servicio = ServicioPagos(
        object(),
        prestamos=object(),
        pagos=object(),
        participaciones=object(),
        ledger=object(),
        auditoria=object(),
        recalculos=object(),
        politicas_pago=object(),
    )

    correlacion_id = servicio._manejador_registro_pago_legacy._nuevo_correlacion_id()

    assert UUID(correlacion_id).version == 4
