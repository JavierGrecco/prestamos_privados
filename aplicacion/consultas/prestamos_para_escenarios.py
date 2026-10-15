"""Consulta los préstamos activos que una persona puede analizar.

Esta lectura se usa para elegir un préstamo en la pantalla de escenarios.
No cambia el cálculo financiero: únicamente arma la lista, respeta los roles
de deudor e inversor y evita mostrar dos veces el mismo préstamo.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


ESTADOS_PRESTAMO_ANALIZABLES = ("ACTIVO", "EN_MORA")


@dataclass(frozen=True)
class PrestamoParaEscenario:
    """Datos mínimos que necesita el selector de préstamos."""

    id: int
    numero: str
    estado: str
    fecha_inicio: date | None
    destino: str | None


@dataclass(frozen=True)
class ParticipacionParaEscenario:
    """Vínculo entre una persona inversora y el préstamo en que participa."""

    prestamo_id: int
    estado: str


class ConsultaPrestamosParaEscenarios(Protocol):
    """Contrato de lectura; la aplicación no necesita conocer SQLite."""

    def prestamos_por_deudor(
        self, persona_id: int
    ) -> tuple[PrestamoParaEscenario, ...]:
        """Devuelve los préstamos de los que la persona es deudora."""

    def participaciones_por_inversor(
        self, persona_id: int
    ) -> tuple[ParticipacionParaEscenario, ...]:
        """Devuelve las participaciones registradas para la persona."""

    def prestamo_por_id(
        self, prestamo_id: int
    ) -> PrestamoParaEscenario | None:
        """Busca el préstamo asociado a una participación."""


class PrestamosParaEscenariosQuery:
    """Entrega una lista ordenada, sin duplicados, de préstamos analizables."""

    def __init__(self, consulta: ConsultaPrestamosParaEscenarios) -> None:
        self._consulta = consulta

    def activos_para_persona(
        self, persona_id: int
    ) -> tuple[PrestamoParaEscenario, ...]:
        """Incluye deuda e inversión, priorizando el vínculo de deudor.

        Se conserva el comportamiento previo de la pantalla: solo se ofrecen
        préstamos ACTIVO o EN_MORA, no se repite un préstamo si la misma
        persona también participa como inversora y se ordena del más reciente
        al más antiguo.
        """
        vistos: set[int] = set()
        prestamos: list[PrestamoParaEscenario] = []

        for prestamo in self._consulta.prestamos_por_deudor(persona_id):
            if (
                prestamo.estado in ESTADOS_PRESTAMO_ANALIZABLES
                and prestamo.id not in vistos
            ):
                vistos.add(prestamo.id)
                prestamos.append(prestamo)

        for participacion in self._consulta.participaciones_por_inversor(
            persona_id
        ):
            if (
                participacion.estado != "ACTIVA"
                or participacion.prestamo_id in vistos
            ):
                continue

            prestamo = self._consulta.prestamo_por_id(
                participacion.prestamo_id
            )
            if (
                prestamo is None
                or prestamo.estado not in ESTADOS_PRESTAMO_ANALIZABLES
            ):
                continue

            vistos.add(prestamo.id)
            prestamos.append(prestamo)

        return tuple(
            sorted(
                prestamos,
                key=lambda prestamo: (
                    prestamo.fecha_inicio or date.min,
                    prestamo.id,
                ),
                reverse=True,
            )
        )


__all__ = [
    "ConsultaPrestamosParaEscenarios",
    "ParticipacionParaEscenario",
    "PrestamoParaEscenario",
    "PrestamosParaEscenariosQuery",
]
