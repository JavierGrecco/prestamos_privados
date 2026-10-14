"""Composición concreta del servicio Legacy de pagos para ejecución local.

Toda dependencia de infraestructura se crea en esta frontera. La capa de
aplicación recibe los colaboradores ya ensamblados y no necesita conocer sus
clases SQLite para ejecutar un pago.
"""
from __future__ import annotations

from infraestructura.db import BaseDatos
from infraestructura.repositorios import (
    AuditoriaRepo,
    LedgerRepo,
    PagoRepo,
    ParticipacionRepo,
    PoliticaPagoRepo,
    PrestamoRepo,
    RecalculoRepo,
)
from aplicacion.servicios.pagos_simulacion import ServicioPagosConSimulacion


def crear_servicio_pagos_legacy(db: BaseDatos) -> ServicioPagosConSimulacion:
    """Construye el servicio Legacy completo con repositorios SQLite inyectados.

    Se retorna la variante con simulación para conservar la API histórica
    consumida por la UI local.
    """
    return ServicioPagosConSimulacion(
        db,
        prestamos=PrestamoRepo(db),
        pagos=PagoRepo(db),
        participaciones=ParticipacionRepo(db),
        ledger=LedgerRepo(db),
        auditoria=AuditoriaRepo(db),
        recalculos=RecalculoRepo(db),
        politicas_pago=PoliticaPagoRepo(db),
    )


__all__ = ["crear_servicio_pagos_legacy"]
