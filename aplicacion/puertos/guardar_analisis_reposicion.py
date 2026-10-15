"""Puerto de escritura para guardar un análisis de reposición.

El puerto expone las dos operaciones atómicas que ya existen en el
repositorio: crear plan+primera versión, o agregar una versión inmutable.
No define cálculos ni altera el contenido del snapshot.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Protocol


class RepositorioGuardadoAnalisis(Protocol):
    """Persistencia necesaria para crear un plan o guardar su nueva versión."""

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
        """Crea el plan y su versión inicial en una única transacción."""

    def guardar_nueva_version(
        self,
        plan_id: int,
        *,
        datos: dict[str, Any],
        creado_por: str,
    ) -> int:
        """Guarda una versión sin modificar las versiones anteriores."""


__all__ = ["RepositorioGuardadoAnalisis"]
