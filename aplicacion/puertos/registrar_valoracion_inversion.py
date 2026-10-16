"""Puerto de escritura para registrar valuaciones declaradas de inversión.

El contrato separa el formulario del simulador de la persistencia. Las reglas
monetarias, validaciones, hash y transacción continúan en el repositorio.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol


class RepositorioValuacionesInversion(Protocol):
    """Contrato para registrar una valuación al cierre o corte informado."""

    def registrar_valoracion_inversion(
        self,
        plan_id: int,
        *,
        fecha_valuacion: date,
        moneda: str,
        valor_original: Decimal,
        cotizacion_ars_por_usd: Decimal | None = None,
        naturaleza_cotizacion: str | None = None,
        fuente_cotizacion: str = "",
        referencia: str = "",
        nota: str = "",
        creado_por: str,
    ) -> int:
        """Registra la valuación declarada y devuelve su identificador."""


__all__ = ["RepositorioValuacionesInversion"]
