"""Contrato mínimo de identidad para generar reportes por persona."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PersonaReporteLectura:
    """Datos públicos de persona que se muestran en el encabezado del reporte."""

    persona_id: int
    nombre_completo: str


class ConsultaPersonaParaReporte(Protocol):
    """Consulta de solo lectura para identificar a quien pertenece el reporte."""

    def persona_para_reporte(
        self, persona_id: int
    ) -> PersonaReporteLectura | None: ...


__all__ = ["PersonaReporteLectura", "ConsultaPersonaParaReporte"]
