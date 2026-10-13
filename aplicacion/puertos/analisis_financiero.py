"""Contratos de lectura para el análisis financiero de una persona.

Estos tipos describen los datos que necesita el análisis. No exponen filas
SQLite ni obligan a la aplicación a conocer repositorios concretos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class PrestamoAnalisis:
    """Datos del préstamo necesarios para flujos y escenarios."""

    id: int
    numero: str
    estado: str
    fecha_inicio: date | None
    tc_inicial: Decimal | None
    capital_original: Decimal
    plazo_meses: int
    sistema: str


@dataclass(frozen=True)
class ParticipacionAnalisis:
    """Aporte y participación histórica de una persona inversora."""

    prestamo_id: int
    estado: str
    capital_aportado: Decimal
    fecha_aporte: date | None
    tc_aporte: Decimal | None
    capital_usd_ref: Decimal | None
    porcentaje: Decimal


@dataclass(frozen=True)
class PagoDeudorAnalisis:
    """Datos del pago real usados para reconstruir el flujo del deudor."""

    fecha_real: date
    monto_moneda_contractual: Decimal
    monto_usd_ref: Decimal | None
    tc_aplicado: Decimal | None


@dataclass(frozen=True)
class CobroLedgerAnalisis:
    """Movimiento real del inversor y sus metadatos de correlación."""

    debe: Decimal
    fecha: date
    metadata: str | None


@dataclass(frozen=True)
class PagoAsociadoCobroAnalisis:
    """Pago persistido que puede vincularse a un cobro del inversor."""

    prestamo_id: int
    fecha_real: date
    monto_usd_ref: Decimal | None
    tc_aplicado: Decimal | None
    prestamo_numero: str


@dataclass(frozen=True)
class CuotaAnalisis:
    """Datos de una cuota que todavía tiene saldo pendiente."""

    id: int
    numero: int
    fecha_vencimiento: date
    estado: str
    cuota: Decimal
    capital: Decimal
    monto_pendiente: Decimal
    interes_pendiente: Decimal
    capital_pendiente: Decimal
    mora_pendiente: Decimal
    tuvo_pago_parcial: bool


@dataclass(frozen=True)
class TasaActivaAnalisis:
    """Modalidad y tasa actualmente registradas para un préstamo."""

    modalidad: str
    tasa_anual: Decimal


class ConsultaAnalisisFinanciero(Protocol):
    """Puerto de solo lectura que necesita el análisis financiero."""

    def prestamos_por_deudor(self, persona_id: int) -> tuple[PrestamoAnalisis, ...]: ...

    def participaciones_por_inversor(
        self, persona_id: int
    ) -> tuple[ParticipacionAnalisis, ...]: ...

    def pagos_validos_de_prestamo(
        self, prestamo_id: int, hasta: date
    ) -> tuple[PagoDeudorAnalisis, ...]: ...

    def cobros_de_inversor(
        self, persona_id: int, hasta: date
    ) -> tuple[CobroLedgerAnalisis, ...]: ...

    def pago_para_cobro(
        self, pago_id: int
    ) -> PagoAsociadoCobroAnalisis | None: ...

    def numero_prestamo(self, prestamo_id: int) -> str: ...

    def prestamo_por_id(self, prestamo_id: int) -> PrestamoAnalisis | None: ...

    def version_activa(self, prestamo_id: int) -> int | None: ...

    def cuotas_proyectadas(
        self, version_id: int, desde: date
    ) -> tuple[CuotaAnalisis, ...]: ...

    def cuotas_pendientes_capital(
        self, version_id: int
    ) -> tuple[CuotaAnalisis, ...]: ...

    def tasa_activa(self, prestamo_id: int) -> TasaActivaAnalisis | None: ...


__all__ = [
    "PrestamoAnalisis",
    "ParticipacionAnalisis",
    "PagoDeudorAnalisis",
    "CobroLedgerAnalisis",
    "PagoAsociadoCobroAnalisis",
    "CuotaAnalisis",
    "TasaActivaAnalisis",
    "ConsultaAnalisisFinanciero",
]
