"""Puerto de lectura del historial de aportes destinados a reposición."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol, Sequence


class AporteHistorialReposicionRecord(Protocol):
    """Campos persistidos que presenta el historial de aportes."""

    id: int
    fecha_aporte: date
    monto_ars: Decimal
    cotizacion_ars_por_usd: Decimal
    equivalente_usd: Decimal
    naturaleza_cotizacion: str
    fuente_cotizacion: str | None
    referencia: str | None


class FuenteHistorialAportesReposicion(Protocol):
    """Fuente que lista aportes en el orden cronológico definido por el repositorio."""

    def listar_aportes(
        self, plan_id: int, limite: int = 200
    ) -> Sequence[AporteHistorialReposicionRecord]:
        """Lista los aportes existentes sin recalcular su cotización histórica."""


__all__ = [
    "AporteHistorialReposicionRecord",
    "FuenteHistorialAportesReposicion",
]
