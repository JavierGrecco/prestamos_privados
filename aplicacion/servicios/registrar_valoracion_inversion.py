"""Caso de uso para registrar una valuación declarada de inversión.

No calcula XIRR ni decide el valor de mercado. Recibe el dato declarado por el
usuario y delega su validación, conversión, escritura y huella al puerto.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from aplicacion.puertos.registrar_valoracion_inversion import (
    RepositorioValuacionesInversion,
)


class ServicioRegistrarValoracionInversion:
    """Coordina el registro de una valuación sin conocer SQLite."""

    def __init__(self, repositorio: RepositorioValuacionesInversion) -> None:
        self._repositorio = repositorio

    def registrar(
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
        """Registra los datos tal como fueron declarados, sin recalcularlos."""
        return self._repositorio.registrar_valoracion_inversion(
            plan_id,
            fecha_valuacion=fecha_valuacion,
            moneda=moneda,
            valor_original=valor_original,
            cotizacion_ars_por_usd=cotizacion_ars_por_usd,
            naturaleza_cotizacion=naturaleza_cotizacion,
            fuente_cotizacion=fuente_cotizacion,
            referencia=referencia,
            nota=nota,
            creado_por=creado_por,
        )


__all__ = ["ServicioRegistrarValoracionInversion"]
