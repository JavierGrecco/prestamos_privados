"""Contratos y DTO públicos para la lectura auditable de pagos V3.

Los tipos describen hechos leídos y conciliados. No dependen de SQLite ni
contienen acceso a repositorios concretos.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol


@dataclass(frozen=True)
class ImputacionPagoV3Read:
    id: int
    cuota_id: int | None
    concepto: str
    monto: Decimal
    origen: str
    referencias_devengamiento: tuple[str, ...]


@dataclass(frozen=True)
class MovimientoLedgerPagoV3Read:
    id: int
    entidad: str
    entidad_id: int
    tipo_movimiento: str
    debe: Decimal
    haber: Decimal
    fecha: str
    correlacion_id: str


@dataclass(frozen=True)
class AuditoriaPagoV3Read:
    id: int
    fecha: str
    usuario: str
    operacion: str
    entidad: str
    entidad_id: int | None
    motivo: str | None
    correlacion_id: str


@dataclass(frozen=True)
class ReconciliacionPagoV3Read:
    monto_pago: Decimal
    suma_imputaciones: Decimal
    suma_ledger_pago_debe: Decimal
    suma_ledger_prestamo_haber: Decimal
    suma_distribucion_inversores: Decimal
    hay_distribucion_inversores: bool

    @property
    def dinero_conservado(self) -> bool:
        return self.suma_imputaciones == self.monto_pago

    @property
    def ledger_pago_balanceado(self) -> bool:
        return (
            self.suma_ledger_pago_debe == self.monto_pago
            and self.suma_ledger_prestamo_haber == self.monto_pago
        )

    @property
    def distribucion_balanceada(self) -> bool:
        if not self.hay_distribucion_inversores:
            return True
        return self.suma_distribucion_inversores == self.monto_pago

    @property
    def integra(self) -> bool:
        return (
            self.dinero_conservado
            and self.ledger_pago_balanceado
            and self.distribucion_balanceada
        )


@dataclass(frozen=True)
class PagoV3Read:
    pago_id: int
    prestamo_id: int
    fecha_real: str
    fecha_valor: str
    monto: Decimal
    moneda: str
    tipo_pago: str
    monto_a_capital: Decimal
    intereses_ahorrados: Decimal
    cuotas_restantes_antes: int
    cuotas_restantes_despues: int
    opcion_adelanto: str | None
    motor_version: str
    plan_hash: str | None
    plan: Any | None
    imputaciones: tuple[ImputacionPagoV3Read, ...]
    ledger: tuple[MovimientoLedgerPagoV3Read, ...]
    auditoria: tuple[AuditoriaPagoV3Read, ...]
    reconciliacion: ReconciliacionPagoV3Read


class ConsultaPagoV3Auditable(Protocol):
    """Puerto que recupera un pago ya conciliado y validado."""

    def obtener_pago_v3(self, pago_id: int) -> PagoV3Read: ...


__all__ = [
    "ImputacionPagoV3Read",
    "MovimientoLedgerPagoV3Read",
    "AuditoriaPagoV3Read",
    "ReconciliacionPagoV3Read",
    "PagoV3Read",
    "ConsultaPagoV3Auditable",
]
