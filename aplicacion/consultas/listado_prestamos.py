"""Consulta de lectura para el listado de préstamos de una persona.

La aplicación decide filtros, roles y duplicados. La persistencia concreta
solo aporta datos y localiza la próxima cuota pendiente.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal, Protocol


ESTADOS_POR_FILTRO: dict[str, frozenset[str] | None] = {
    "ACTIVOS": frozenset({"ACTIVO", "EN_MORA"}),
    "FINALIZADOS": frozenset({"FINALIZADO"}),
    "CANCELADOS": frozenset({"CANCELADO"}),
    "REFINANCIADOS": frozenset({"REFINANCIADO"}),
    "TODOS": None,
}


@dataclass(frozen=True)
class PrestamoListado:
    """Información del préstamo que necesita la tarjeta de la interfaz."""

    id: int
    numero: str
    estado: str
    fecha_inicio: date | None
    destino: str | None
    capital_original: Decimal


@dataclass(frozen=True)
class ParticipacionListado:
    """Datos de una participación que pueden cambiar cómo se muestra el rol."""

    prestamo_id: int
    estado: str
    capital_aportado: Decimal


@dataclass(frozen=True)
class CuotaProximaListado:
    """Campos de la próxima cuota que se presentan en el listado."""

    estado: str
    fecha_vencimiento: date | None


@dataclass(frozen=True)
class ItemListadoPrestamo:
    """Préstamo listo para mostrar, con el rol y el importe de esa persona."""

    prestamo: PrestamoListado
    rol: Literal["deudor", "inversor"]
    monto: Decimal
    proxima_cuota: CuotaProximaListado | None


class FuenteListadoPrestamos(Protocol):
    """Contrato de lectura que oculta repositorios y base de datos."""

    def prestamos_por_deudor(
        self, persona_id: int
    ) -> tuple[PrestamoListado, ...]:
        """Lista préstamos de los que la persona es deudora."""

    def participaciones_por_inversor(
        self, persona_id: int
    ) -> tuple[ParticipacionListado, ...]:
        """Lista participaciones de la persona, respetando el orden persistido."""

    def prestamo_por_id(self, prestamo_id: int) -> PrestamoListado | None:
        """Obtiene un préstamo asociado a una participación."""

    def proxima_cuota(
        self, prestamo_id: int
    ) -> CuotaProximaListado | None:
        """Devuelve la primera cuota pendiente de la versión activa."""


class ConsultaListadoPrestamos:
    """Arma el listado sin conocer SQLite ni los modelos de persistencia."""

    def __init__(self, fuente: FuenteListadoPrestamos) -> None:
        self._fuente = fuente

    def por_persona(
        self, persona_id: int, estado_filtro: str = "ACTIVOS"
    ) -> tuple[ItemListadoPrestamo, ...]:
        """Incluye deuda e inversión activa sin duplicar un mismo préstamo.

        Se conserva la prioridad histórica: primero los préstamos deudores
        (ordenados por el repositorio), luego las inversiones activas. Si la
        persona tiene ambos roles sobre un préstamo, se muestra como deudora.
        """
        estados = ESTADOS_POR_FILTRO.get(estado_filtro)

        def incluir(prestamo: PrestamoListado) -> bool:
            return estados is None or prestamo.estado in estados

        resultados: list[ItemListadoPrestamo] = []
        vistos: set[int] = set()

        for prestamo in self._fuente.prestamos_por_deudor(persona_id):
            if not incluir(prestamo):
                continue
            vistos.add(prestamo.id)
            resultados.append(
                ItemListadoPrestamo(
                    prestamo=prestamo,
                    rol="deudor",
                    monto=prestamo.capital_original,
                    proxima_cuota=self._fuente.proxima_cuota(prestamo.id),
                )
            )

        for participacion in self._fuente.participaciones_por_inversor(persona_id):
            if participacion.estado != "ACTIVA":
                continue
            if participacion.prestamo_id in vistos:
                continue

            prestamo = self._fuente.prestamo_por_id(participacion.prestamo_id)
            if prestamo is None or not incluir(prestamo):
                continue

            vistos.add(prestamo.id)
            resultados.append(
                ItemListadoPrestamo(
                    prestamo=prestamo,
                    rol="inversor",
                    monto=participacion.capital_aportado,
                    proxima_cuota=self._fuente.proxima_cuota(prestamo.id),
                )
            )

        return tuple(resultados)


__all__ = [
    "ConsultaListadoPrestamos",
    "CuotaProximaListado",
    "FuenteListadoPrestamos",
    "ItemListadoPrestamo",
    "ParticipacionListado",
    "PrestamoListado",
]
