"""Contrato de lectura e información tipada del historial auditable de pagos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class PagoAuditable:
    id: int
    prestamo_id: int
    prestamo_numero: str
    fecha_real: date
    fecha_valor: date
    fecha_registro: str
    monto: Decimal
    moneda: str
    estado: str
    medio: str | None
    referencia: str | None
    nota: str | None
    creado_por: str | None
    tipo_pago: str
    monto_a_capital: Decimal
    intereses_ahorrados: Decimal
    cuotas_restantes_antes: int
    cuotas_restantes_despues: int
    opcion_adelanto: str | None
    motor_version: str
    plan_hash: str | None
    plan_json: str | None
    idempotency_key: str | None
    idempotency_fingerprint: str | None
    motivo_anulacion: str | None


@dataclass(frozen=True)
class EvidenciaPagoAuditable:
    pago: PagoAuditable
    imputaciones: tuple[dict, ...]
    devengamientos: tuple[dict, ...]
    ledger: tuple[dict, ...]
    auditoria: tuple[dict, ...]
    observaciones_sombra: tuple[dict, ...]
    plan: dict | None

    @property
    def correlacion_id(self) -> str | None:
        for movimiento in self.ledger:
            if movimiento.get("entidad") == "PAGO":
                return movimiento.get("correlacion_id")
        return None


class ConsultaHistorialPagos(Protocol):
    """Consulta de solo lectura para reconstruir hechos ya persistidos."""

    def por_persona(
        self, persona_id: int, *, limite: int = 100
    ) -> tuple[PagoAuditable, ...]: ...

    def por_prestamo(
        self, prestamo_id: int, *, limite: int = 100
    ) -> tuple[PagoAuditable, ...]: ...

    def detalle(self, pago_id: int) -> EvidenciaPagoAuditable | None: ...


__all__ = [
    "PagoAuditable",
    "EvidenciaPagoAuditable",
    "ConsultaHistorialPagos",
]
