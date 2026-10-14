"""Adaptador SQLite para obtener el nombre de una persona en reportes."""

from __future__ import annotations

from aplicacion.puertos.reportes_persona import PersonaReporteLectura
from infraestructura.repositorios import PersonaRepo


class ReportesPersonaSQLiteQuery:
    """Traduce el modelo de persona al contrato público de los reportes."""

    def __init__(self, db) -> None:
        self._personas = PersonaRepo(db)

    def persona_para_reporte(
        self, persona_id: int
    ) -> PersonaReporteLectura | None:
        persona = self._personas.obtener(persona_id)
        if persona is None:
            return None

        nombre = getattr(persona, "nombre_completo", None) or (
            f"{persona.nombre} {persona.apellido}".strip()
        )
        return PersonaReporteLectura(
            persona_id=persona_id,
            nombre_completo=str(nombre),
        )


__all__ = ["ReportesPersonaSQLiteQuery"]
