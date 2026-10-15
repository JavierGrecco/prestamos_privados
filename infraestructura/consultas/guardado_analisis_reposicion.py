"""Adaptador para guardar un análisis mediante el repositorio local existente.

El adaptador no replica reglas: deriva creación, versiones inmutables,
validaciones y transacciones al repositorio que ya las implementa.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from infraestructura.repositorios import PlanesReposicionRepo


class GuardadoAnalisisReposicionSQLite:
    """Implementación SQLite del puerto de guardado de análisis."""

    def __init__(self, db) -> None:
        self._repo = PlanesReposicionRepo(db)

    def crear_plan_con_snapshot(
        self,
        *,
        nombre: str,
        tipo_plan: str,
        fecha_desembolso: date,
        capital_original_ars: Decimal,
        datos: dict[str, Any],
        creado_por: str,
    ) -> tuple[int, int]:
        return self._repo.crear_plan_con_snapshot(
            nombre=nombre,
            tipo_plan=tipo_plan,
            fecha_desembolso=fecha_desembolso,
            capital_original_ars=capital_original_ars,
            datos=datos,
            creado_por=creado_por,
        )

    def guardar_nueva_version(
        self, plan_id: int, *, datos: dict[str, Any], creado_por: str
    ) -> int:
        return self._repo.guardar_nueva_version(
            plan_id, datos=datos, creado_por=creado_por
        )


__all__ = ["GuardadoAnalisisReposicionSQLite"]
