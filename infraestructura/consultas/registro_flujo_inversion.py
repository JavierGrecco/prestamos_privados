"""Adaptador SQLite para registrar movimientos declarados de inversión."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from infraestructura.repositorios import PlanesReposicionRepo


class RegistroFlujoInversionSQLite:
    """Delega las reglas y la transacción en el repositorio existente."""

    def __init__(self, db) -> None:
        self._repo = PlanesReposicionRepo(db)

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
        return self._repo.registrar_flujo_inversion(
            plan_id,
            fecha_flujo=fecha_flujo,
            tipo_flujo=tipo_flujo,
            moneda=moneda,
            monto_original=monto_original,
            cotizacion_ars_por_usd=cotizacion_ars_por_usd,
            naturaleza_cotizacion=naturaleza_cotizacion,
            fuente_cotizacion=fuente_cotizacion,
            referencia=referencia,
            nota=nota,
            creado_por=creado_por,
        )


__all__ = ["RegistroFlujoInversionSQLite"]
