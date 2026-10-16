"""Caso de uso para cerrar un plan de reposición.

El servicio coordina la petición y deja las validaciones, el control de estado,
la transacción y la escritura de auditoría a cargo del repositorio existente.
No elimina ni reescribe versiones, aportes o movimientos del plan.
"""
from __future__ import annotations

from aplicacion.puertos.cerrar_plan_reposicion import RepositorioCierrePlan


class ServicioCerrarPlanReposicion:
    """Cierra un plan mediante el contrato de persistencia."""

    def __init__(self, repositorio: RepositorioCierrePlan) -> None:
        self._repositorio = repositorio

    def cerrar(self, plan_id: int, *, cerrado_por: str) -> None:
        """Solicita el cierre y propaga cualquier error de validación."""
        self._repositorio.cerrar_plan(plan_id, cerrado_por=cerrado_por)


__all__ = ["ServicioCerrarPlanReposicion"]
