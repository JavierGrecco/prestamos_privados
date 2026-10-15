"""Lectura SQLite para el selector de préstamos de escenarios.

Este adaptador utiliza los repositorios existentes y traduce sus modelos a
los datos mínimos que expone la aplicación. El filtrado por estado, la
eliminación de duplicados y el orden pertenecen a la consulta de aplicación.
"""
from __future__ import annotations

from aplicacion.consultas.prestamos_para_escenarios import (
    ParticipacionParaEscenario,
    PrestamoParaEscenario,
)
from infraestructura.repositorios import ParticipacionRepo, PrestamoRepo


class PrestamosParaEscenariosSQLiteQuery:
    """Consulta préstamos por persona usando la persistencia actual."""

    def __init__(self, db) -> None:
        self._prestamos = PrestamoRepo(db)
        self._participaciones = ParticipacionRepo(db)

    def prestamos_por_deudor(
        self, persona_id: int
    ) -> tuple[PrestamoParaEscenario, ...]:
        return tuple(
            _convertir_prestamo(prestamo)
            for prestamo in self._prestamos.listar(deudor_id=persona_id)
        )

    def participaciones_por_inversor(
        self, persona_id: int
    ) -> tuple[ParticipacionParaEscenario, ...]:
        return tuple(
            ParticipacionParaEscenario(
                prestamo_id=int(participacion.prestamo_id),
                estado=str(participacion.estado),
            )
            for participacion in self._participaciones.por_inversor(persona_id)
        )

    def prestamo_por_id(
        self, prestamo_id: int
    ) -> PrestamoParaEscenario | None:
        prestamo = self._prestamos.obtener(prestamo_id)
        return None if prestamo is None else _convertir_prestamo(prestamo)


def _convertir_prestamo(prestamo) -> PrestamoParaEscenario:
    """Oculta el modelo de persistencia detrás del contrato de aplicación."""
    return PrestamoParaEscenario(
        id=int(prestamo.id),
        numero=str(prestamo.numero),
        estado=str(prestamo.estado),
        fecha_inicio=prestamo.fecha_inicio,
        destino=prestamo.destino,
    )


__all__ = ["PrestamosParaEscenariosSQLiteQuery"]
