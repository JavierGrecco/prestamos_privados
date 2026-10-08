"""Casos de uso de consulta de auditoría.

La capa expuesta a Streamlit es de solo lectura y no permite modificar ni
eliminar evidencia.
"""
from __future__ import annotations

from dataclasses import dataclass

from infraestructura.repositorios.auditoria import AuditoriaRepo
from infraestructura.repositorios.modelos import EntradaAuditoria


@dataclass(frozen=True)
class FiltrosAuditoria:
    usuario: str | None = None
    operacion: str | None = None
    entidad: str | None = None
    limite: int = 200


class ServicioAuditoria:
    """Consulta evidencia de auditoría sin mutar la base."""

    def __init__(self, db) -> None:
        self._repo = AuditoriaRepo(db)

    def listar(self, filtros: FiltrosAuditoria | None = None) -> list[EntradaAuditoria]:
        filtros = filtros or FiltrosAuditoria()
        return self._repo.listar(
            limite=filtros.limite,
            usuario=filtros.usuario,
            operacion=filtros.operacion,
            entidad=filtros.entidad,
        )

    def operaciones(self) -> list[str]:
        return self._repo.operaciones()

    def entidades(self) -> list[str]:
        return self._repo.entidades()

    def por_correlacion(self, correlacion_id: str) -> list[EntradaAuditoria]:
        if not correlacion_id or not correlacion_id.strip():
            raise ValueError("Se requiere una correlación")
        return self._repo.por_correlacion(correlacion_id.strip())
