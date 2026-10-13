"""Fachada de aplicación para consultar historial y evidencia de pagos.

No ejecuta SQL ni modifica hechos financieros. Las lecturas persistidas se
resuelven mediante el contrato público de historial auditable.
"""

from __future__ import annotations

from aplicacion.puertos.historial_pagos import (
    ConsultaHistorialPagos,
    EvidenciaPagoAuditable,
    PagoAuditable,
)


class HistorialPagosQuery:
    """Expone el historial de pagos mediante un lector ya compuesto."""

    def __init__(self, consulta: ConsultaHistorialPagos) -> None:
        self._consulta = consulta

    def por_persona(
        self,
        persona_id: int,
        *,
        limite: int = 100,
    ) -> tuple[PagoAuditable, ...]:
        return self._consulta.por_persona(persona_id, limite=limite)

    def por_prestamo(
        self,
        prestamo_id: int,
        *,
        limite: int = 100,
    ) -> tuple[PagoAuditable, ...]:
        return self._consulta.por_prestamo(prestamo_id, limite=limite)

    def detalle(self, pago_id: int) -> EvidenciaPagoAuditable | None:
        return self._consulta.detalle(pago_id)


__all__ = [
    "PagoAuditable",
    "EvidenciaPagoAuditable",
    "HistorialPagosQuery",
]
