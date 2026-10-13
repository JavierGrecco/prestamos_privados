"""Contratos de lectura para el detalle financiero histórico de un préstamo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class PrestamoDetalleLectura:
    prestamo_id: int
    numero: str
    capital_original: Decimal
    fecha_inicio: date | None


@dataclass(frozen=True, slots=True)
class CuotaDetalleLectura:
    id: int
    numero: int
    vencimiento: date
    estado: str
    capital_inicial: Decimal
    interes: Decimal
    capital: Decimal
    cuota: Decimal
    saldo: Decimal
    monto_pendiente: Decimal
    interes_pendiente: Decimal | None
    capital_pendiente: Decimal | None
    mora_pendiente: Decimal
    fue_mora: bool
    tuvo_pago_parcial: bool
    fue_recalculada: bool


@dataclass(frozen=True, slots=True)
class DevengamientoDetalleLectura:
    id: int
    cuota_id: int | None
    concepto: str
    monto: Decimal
    fecha_desde: date
    fecha_hasta: date
    origen: str
    referencia: str | None
    base: Decimal
    tasa_anual: Decimal
    dias: int
    motor_version: str


@dataclass(frozen=True, slots=True)
class RecalculoDetalleLectura:
    id: int
    pago_id: int
    tipo: str
    fecha: date
    capital_antes: Decimal
    capital_despues: Decimal
    cuotas_antes: int
    cuotas_despues: int
    intereses_antes: Decimal
    intereses_despues: Decimal
    detalle_json: str | None


@dataclass(frozen=True, slots=True)
class ImputacionCapitalDetalleLectura:
    pago_id: int
    fecha_valor: date
    tipo_pago: str | None
    monto: Decimal


class ConsultaDetalleFinancieroPrestamo(Protocol):
    """Solo lecturas persistidas necesarias para elaborar el read model."""

    def obtener_prestamo(self, prestamo_id: int) -> PrestamoDetalleLectura | None: ...

    def version_activa(self, prestamo_id: int) -> int | None: ...

    def cuotas(self, version_id: int) -> Sequence[CuotaDetalleLectura]: ...

    def devengamientos(
        self, prestamo_id: int
    ) -> Sequence[DevengamientoDetalleLectura]: ...

    def recalculos(
        self, prestamo_id: int
    ) -> Sequence[RecalculoDetalleLectura]: ...

    def imputaciones_capital(
        self, prestamo_id: int
    ) -> Sequence[ImputacionCapitalDetalleLectura]: ...


__all__ = [
    "PrestamoDetalleLectura",
    "CuotaDetalleLectura",
    "DevengamientoDetalleLectura",
    "RecalculoDetalleLectura",
    "ImputacionCapitalDetalleLectura",
    "ConsultaDetalleFinancieroPrestamo",
]
