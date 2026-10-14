"""Contratos de lectura para los resúmenes de impacto de pagos.

Los contratos solo describen los datos que necesita la consulta. No exponen
conexiones, filas SQLite ni repositorios concretos.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol, Sequence


class CuotaImpactoPagoLectura(Protocol):
    """Datos de la cuota que se muestran en el resumen de impacto."""

    numero: int
    mora_pendiente: Decimal
    fue_mora: bool


class PagoImpactoPagoLectura(Protocol):
    """Datos de un pago usados por el resumen y el historial de decisiones."""

    estado: str
    tipo_pago: str | None
    fecha_real: date | None
    interes_extra_generado: Decimal
    intereses_ahorrados: Decimal
    monto_a_capital: Decimal


class ConsultaCuotasImpactoPago(Protocol):
    """Lecturas mínimas de cuotas necesarias para evaluar el impacto."""

    def version_activa(self, prestamo_id: int) -> int | None: ...

    def cuotas(self, version_id: int) -> Sequence[CuotaImpactoPagoLectura]: ...


class ConsultaPagosImpactoPago(Protocol):
    """Lecturas de pagos de un préstamo."""

    def por_prestamo(self, prestamo_id: int) -> Sequence[PagoImpactoPagoLectura]: ...


__all__ = [
    "CuotaImpactoPagoLectura",
    "PagoImpactoPagoLectura",
    "ConsultaCuotasImpactoPago",
    "ConsultaPagosImpactoPago",
]
