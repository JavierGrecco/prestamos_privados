"""Puerto para registrar un aporte destinado a reponer capital.

El puerto describe los datos que necesita la operación. Las validaciones
financieras, el cálculo de equivalencia y la escritura auditada siguen a cargo
del repositorio que ya implementa esas reglas.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol


class RepositorioAportesReposicion(Protocol):
    """Contrato de escritura de un aporte en moneda local."""

    def registrar_aporte(
        self,
        plan_id: int,
        *,
        fecha_aporte: date,
        monto_ars: Decimal,
        cotizacion_ars_por_usd: Decimal,
        naturaleza_cotizacion: str,
        fuente_cotizacion: str,
        referencia: str,
        nota: str,
        creado_por: str,
    ) -> int:
        """Registra el aporte y devuelve su identificador persistido."""


__all__ = ["RepositorioAportesReposicion"]
