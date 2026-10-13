"""Casos de uso de consulta de auditoría.

La capa expuesta a Streamlit es de solo lectura y no permite modificar ni
eliminar evidencia. El acceso a persistencia se recibe por el puerto público.
"""
from __future__ import annotations

from dataclasses import dataclass

from aplicacion.puertos.auditoria import ConsultaAuditoria, EventoAuditoria


@dataclass(frozen=True)
class FiltrosAuditoria:
    usuario: str | None = None
    operacion: str | None = None
    entidad: str | None = None
    limite: int = 200


class ServicioAuditoria:
    """Consulta evidencia de auditoría sin mutar la base."""

    def __init__(self, consulta: ConsultaAuditoria) -> None:
        self._consulta = consulta

    def listar(self, filtros: FiltrosAuditoria | None = None) -> list[EventoAuditoria]:
        filtros = filtros or FiltrosAuditoria()
        return self._consulta.listar(
            limite=filtros.limite,
            usuario=filtros.usuario,
            operacion=filtros.operacion,
            entidad=filtros.entidad,
        )

    def operaciones(self) -> list[str]:
        return self._consulta.operaciones()

    def entidades(self) -> list[str]:
        return self._consulta.entidades()

    def por_correlacion(self, correlacion_id: str) -> list[EventoAuditoria]:
        if not correlacion_id or not correlacion_id.strip():
            raise ValueError("Se requiere una correlación")
        return self._consulta.por_correlacion(correlacion_id.strip())
