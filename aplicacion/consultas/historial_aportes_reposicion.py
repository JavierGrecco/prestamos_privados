"""Consulta de lectura para el historial de aportes de reposición."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aplicacion.puertos.historial_aportes_reposicion import (
    FuenteHistorialAportesReposicion,
)


@dataclass(frozen=True)
class AporteHistorialReposicion:
    """Datos que necesita la tabla de aportes del simulador."""

    id: int
    fecha_aporte: date
    monto_ars: Decimal
    cotizacion_ars_por_usd: Decimal
    equivalente_usd: Decimal
    naturaleza_cotizacion: str
    fuente_cotizacion: str | None
    referencia: str | None


class ConsultaHistorialAportesReposicion:
    """Traduce los registros a DTOs y conserva el orden que devuelve la fuente."""

    def __init__(self, fuente: FuenteHistorialAportesReposicion) -> None:
        self._fuente = fuente

    def listar(self, plan_id: int) -> tuple[AporteHistorialReposicion, ...]:
        """Lista aportes conservando la cotización y el equivalente originales."""
        return tuple(
            AporteHistorialReposicion(
                id=int(aporte.id),
                fecha_aporte=aporte.fecha_aporte,
                monto_ars=aporte.monto_ars,
                cotizacion_ars_por_usd=aporte.cotizacion_ars_por_usd,
                equivalente_usd=aporte.equivalente_usd,
                naturaleza_cotizacion=str(aporte.naturaleza_cotizacion),
                fuente_cotizacion=aporte.fuente_cotizacion,
                referencia=aporte.referencia,
            )
            for aporte in self._fuente.listar_aportes(plan_id, limite=200)
        )


__all__ = [
    "AporteHistorialReposicion",
    "ConsultaHistorialAportesReposicion",
]
