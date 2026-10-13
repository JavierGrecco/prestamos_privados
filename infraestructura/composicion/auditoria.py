"""Composición SQLite del servicio de consulta de auditoría."""

from __future__ import annotations

from aplicacion.servicios.auditoria import ServicioAuditoria
from infraestructura.repositorios.auditoria import AuditoriaRepo


def crear_servicio_auditoria(db) -> ServicioAuditoria:
    """Ensamble el caso de uso de consulta con el repositorio SQLite local."""
    return ServicioAuditoria(AuditoriaRepo(db))


__all__ = ["crear_servicio_auditoria"]
