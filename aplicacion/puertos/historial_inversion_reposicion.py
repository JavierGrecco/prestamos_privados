"""Puerto de lectura del historial de inversión declarada.

La interfaz necesita movimientos, valuaciones y el resumen que ya calcula el
repositorio. El puerto conserva ese límite para no acoplar la UI a SQLite.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol, Sequence


class FlujoInversionHistorialRecord(Protocol):
    id: int
    fecha_flujo: date
    tipo_flujo: str
    moneda: str
    monto_original: Decimal
    equivalente_usd: Decimal
    naturaleza_cotizacion: str
    fuente_cotizacion: str | None
    referencia: str | None


class ValuacionInversionHistorialRecord(Protocol):
    id: int
    fecha_valuacion: date
    moneda: str
    valor_original: Decimal
    equivalente_usd: Decimal
    naturaleza_cotizacion: str
    fuente_cotizacion: str | None
    referencia: str | None


class ResumenRendimientoInversionRecord(Protocol):
    cantidad_flujos: int
    cantidad_valuaciones: int
    fecha_inicio: date | None
    fecha_valuacion: date | None
    aportes_inversion_usd_ref: Decimal
    cobros_y_rescates_usd_ref: Decimal
    costos_externos_usd_ref: Decimal
    valor_mercado_final_usd_ref: Decimal | None
    resultado_total_usd_ref: Decimal | None
    xirr_anual: Decimal | None
    mensaje_xirr: str


class FuenteHistorialInversionReposicion(Protocol):
    """Operaciones de lectura ya soportadas por la persistencia actual."""

    def listar_flujos_inversion(
        self, plan_id: int, limite: int = 100
    ) -> Sequence[FlujoInversionHistorialRecord]:
        """Lista movimientos declarados con el orden histórico existente."""

    def listar_valuaciones_inversion(
        self, plan_id: int, limite: int = 100
    ) -> Sequence[ValuacionInversionHistorialRecord]:
        """Lista valuaciones declaradas con el orden histórico existente."""

    def resumen_rendimiento_inversion(
        self, plan_id: int
    ) -> ResumenRendimientoInversionRecord:
        """Devuelve el resumen calculado y validado por la persistencia."""


__all__ = [
    "FlujoInversionHistorialRecord",
    "FuenteHistorialInversionReposicion",
    "ResumenRendimientoInversionRecord",
    "ValuacionInversionHistorialRecord",
]
