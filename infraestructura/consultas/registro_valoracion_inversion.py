"""Adaptador SQLite para registrar valuaciones usando las reglas actuales."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from infraestructura.repositorios import PlanesReposicionRepo


class RegistroValoracionInversionSQLite:
    """Delega validación, conversión, hash y transacción al repositorio actual."""

    def __init__(self, db) -> None:
        self._repo = PlanesReposicionRepo(db)

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
        return self._repo.registrar_valoracion_inversion(
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


__all__ = ["RegistroValoracionInversionSQLite"]
