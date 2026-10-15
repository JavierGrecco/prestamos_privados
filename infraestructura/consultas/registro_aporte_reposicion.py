"""Adaptador SQLite para registrar aportes con las reglas de persistencia actuales."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from infraestructura.repositorios import PlanesReposicionRepo


class RegistroAporteReposicionSQLite:
    """Deriva el alta de aportes al repositorio existente, sin replicar reglas."""

    def __init__(self, db) -> None:
        self._repo = PlanesReposicionRepo(db)

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
        return self._repo.registrar_aporte(
            plan_id,
            fecha_aporte=fecha_aporte,
            monto_ars=monto_ars,
            cotizacion_ars_por_usd=cotizacion_ars_por_usd,
            naturaleza_cotizacion=naturaleza_cotizacion,
            fuente_cotizacion=fuente_cotizacion,
            referencia=referencia,
            nota=nota,
            creado_por=creado_por,
        )


__all__ = ["RegistroAporteReposicionSQLite"]
