"""Adaptador de consulta de auditoría que traduce el repositorio SQLite al puerto."""

from __future__ import annotations

from aplicacion.puertos.auditoria import EventoAuditoria
from infraestructura.repositorios.auditoria import AuditoriaRepo


class ConsultaAuditoriaSQLite:
    """Lee evidencia auditada sin exponer el modelo del repositorio a aplicación."""

    def __init__(self, db) -> None:
        self._repo = AuditoriaRepo(db)

    def listar(
        self,
        *,
        limite: int = 200,
        usuario: str | None = None,
        operacion: str | None = None,
        entidad: str | None = None,
    ) -> list[EventoAuditoria]:
        return [
            _evento_desde_modelo(item)
            for item in self._repo.listar(
                limite=limite,
                usuario=usuario,
                operacion=operacion,
                entidad=entidad,
            )
        ]

    def operaciones(self, *, limite: int = 100) -> list[str]:
        return self._repo.operaciones(limite=limite)

    def entidades(self, *, limite: int = 100) -> list[str]:
        return self._repo.entidades(limite=limite)

    def por_correlacion(self, correlacion_id: str) -> list[EventoAuditoria]:
        return [
            _evento_desde_modelo(item)
            for item in self._repo.por_correlacion(correlacion_id)
        ]


def _evento_desde_modelo(item) -> EventoAuditoria:
    return EventoAuditoria(
        id=item.id,
        fecha=item.fecha,
        usuario=item.usuario,
        operacion=item.operacion,
        entidad=item.entidad,
        entidad_id=item.entidad_id,
        datos_anteriores=item.datos_anteriores,
        datos_nuevos=item.datos_nuevos,
        motivo=item.motivo,
        correlacion_id=item.correlacion_id,
    )
