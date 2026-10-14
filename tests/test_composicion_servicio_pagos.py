"""Pruebas del ensamblado explícito del servicio Legacy de pagos."""

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
        assert servicio._manejador_registro_pago_legacy.unidad_trabajo is db


def test_fachada_rechaza_inyeccion_parcial(tmp_path):
    with BaseDatos(tmp_path / "composicion-parcial.db") as db:
        with pytest.raises(ValueError, match="inyección requiere todos"):
            ServicioPagos(db, prestamos=PrestamoRepo(db))

def test_constructor_historico_sigue_disponible_como_puente_temporal(tmp_path):
    """El puente se conserva expresamente hasta migrar los consumidores externos."""
    with BaseDatos(tmp_path / "compatibilidad-constructor.db") as db:
        servicio = ServicioPagos(db)

        assert servicio.db is db
        assert isinstance(servicio.prestamos, PrestamoRepo)
        assert isinstance(servicio.pagos, PagoRepo)
        assert isinstance(servicio.participaciones, ParticipacionRepo)
        assert isinstance(servicio.ledger, LedgerRepo)
        assert isinstance(servicio.auditoria, AuditoriaRepo)
        assert isinstance(servicio.recalculos, RecalculoRepo)
        assert isinstance(servicio.politicas_pago, PoliticaPagoRepo)
