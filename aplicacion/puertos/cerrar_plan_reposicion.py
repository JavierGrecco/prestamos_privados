"""Puerto de escritura para cerrar un plan de reposición.

El contrato encapsula la solicitud. Las reglas de estado, el registro de quién
cierra y la transacción quedan en la persistencia actual.
"""
from __future__ import annotations

from typing import Protocol


class RepositorioCierrePlan(Protocol):
    """Contrato para cerrar un plan activo conservando su historial."""

    def cerrar_plan(self, plan_id: int, *, cerrado_por: str) -> None:
        """Cierra el plan o devuelve un error de validación."""


__all__ = ["RepositorioCierrePlan"]
