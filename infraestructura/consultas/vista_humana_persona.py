"""Adaptador SQLite para las lecturas de Mi espacio.

Mantiene el acceso a repositorios en infraestructura y devuelve solo los datos
que necesita la vista humana. No calcula posiciones ni modifica información.
"""

from __future__ import annotations

from decimal import Decimal

from aplicacion.puertos.vista_humana_persona import (
    ParticipacionVistaHumana,
    PersonaVistaHumana,
    PrestamoVistaHumana,
)
from infraestructura.repositorios import ParticipacionRepo, PersonaRepo, PrestamoRepo


class VistaHumanaPersonaSQLiteQuery:
    """Consulta los datos persistidos que la vista humana presenta."""

    def __init__(self, db) -> None:
        self._personas = PersonaRepo(db)
        self._prestamos = PrestamoRepo(db)
        self._participaciones = ParticipacionRepo(db)

    def persona_por_id(self, persona_id: int) -> PersonaVistaHumana | None:
        persona = self._personas.obtener(persona_id)
        if persona is None or persona.id is None:
            return None
        return PersonaVistaHumana(
            id=int(persona.id),
            nombre=str(persona.nombre),
            apellido=str(persona.apellido or ""),
        )

    def roles_por_persona(self, persona_id: int) -> tuple[str, ...]:
        return tuple(self._personas.roles(persona_id))

    def prestamos_por_deudor(
        self, persona_id: int
    ) -> tuple[PrestamoVistaHumana, ...]:
        return tuple(
            _prestamo_para_vista(prestamo)
            for prestamo in self._prestamos.listar(deudor_id=persona_id)
            if prestamo.id is not None
        )

    def prestamo_por_id(self, prestamo_id: int) -> PrestamoVistaHumana | None:
        prestamo = self._prestamos.obtener(prestamo_id)
        if prestamo is None or prestamo.id is None:
            return None
        return _prestamo_para_vista(prestamo)

    def participaciones_por_inversor(
        self, persona_id: int
    ) -> tuple[ParticipacionVistaHumana, ...]:
        return tuple(
            ParticipacionVistaHumana(
                prestamo_id=int(participacion.prestamo_id),
                capital_aportado=Decimal(str(participacion.capital_aportado)),
                porcentaje=Decimal(str(participacion.porcentaje)),
                estado=str(participacion.estado),
            )
            for participacion in self._participaciones.por_inversor(persona_id)
        )


def _prestamo_para_vista(prestamo) -> PrestamoVistaHumana:
    """Traduce el modelo de persistencia al contrato pequeño de presentación."""
    return PrestamoVistaHumana(
        id=int(prestamo.id),
        numero=str(prestamo.numero),
        destino=prestamo.destino,
        estado=str(prestamo.estado),
        capital_original=Decimal(str(prestamo.capital_original)),
    )


__all__ = ["VistaHumanaPersonaSQLiteQuery"]
