"""Puerto de escritura para movimientos declarados de inversión.

El puerto mantiene separado el flujo de inversión del aporte reservado para
reposición de capital. No define el cálculo de equivalencia ni las reglas de
integridad, que siguen bajo responsabilidad del repositorio.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol


class RepositorioFlujosInversion(Protocol):
    """Contrato para registrar un flujo de inversión declarado."""

    def registrar_flujo_inversion(
        self,
        plan_id: int,
        *,
        fecha_flujo: date,
        tipo_flujo: str,
        moneda: str,
        monto_original: Decimal,
        cotizacion_ars_por_usd: Decimal | None = None,
        naturaleza_cotizacion: str | None = None,
        fuente_cotizacion: str = "",
        referencia: str = "",
        nota: str = "",
        creado_por: str,
    ) -> int:
        """Registra el movimiento y devuelve su identificador persistido."""


__all__ = ["RepositorioFlujosInversion"]
