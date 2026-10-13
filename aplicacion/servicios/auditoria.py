"""Casos de uso de consulta de auditoría.

El servicio solo coordina lecturas de evidencia inmutable. La forma de acceder a
la persistencia se inyecta mediante el contrato público de consulta.
"""

from __future__ import annotations

from dataclasses import dataclass

from aplicacion.puertos.auditoria import ConsultaAuditoria, EntradaAuditoria


@dataclass(frozen=True, slots=True)
class FiltrosAuditoria:
    usuario: str | None = None
    operacion: str | None = None
    entidad: str | None = None
    limite: int = 200


class ServicioAuditoria:
    """Consulta evidencia de auditoría sin mutar la base."""

    def __init__(self, consulta: ConsultaAuditoria) -> None:
        self._consulta = consulta

    def listar(self, filtros: FiltrosAuditoria | None = None) -> list[EntradaAuditoria]:
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

    def por_correlacion(self, correlacion_id: str) -> list[EntradaAuditoria]:
        if not correlacion_id or not correlacion_id.strip():
            raise ValueError("Se requiere una correlación")
        return self._consulta.por_correlacion(correlacion_id.strip())
