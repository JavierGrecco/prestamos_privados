"""Contratos de los datos que necesita la gestión de personas.

Las interfaces describen las operaciones del caso de uso; los repositorios
SQLite y su composición concreta permanecen en infraestructura.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class RepositorioPersonas(Protocol):
    def listar(
        self,
        estado: str | None = None,
        rol: str | None = None,
    ) -> Sequence[Any]: ...

    def obtener(self, persona_id: int) -> Any | None: ...

    def crear(
        self,
        nombre: str,
        apellido: str = "",
        documento: str | None = None,
        telefono: str | None = None,
        email: str | None = None,
        domicilio: str | None = None,
        notas: str | None = None,
    ) -> int: ...

    def actualizar(self, persona_id: int, **campos: Any) -> None: ...

    def agregar_rol(self, persona_id: int, rol: str) -> None: ...

    def quitar_rol(
        self, persona_id: int, rol: str, motivo: str = ""
    ) -> None: ...

    def roles(self, persona_id: int) -> Sequence[str]: ...


class ConsultaPrestamosPersona(Protocol):
    """Consultas de préstamos necesarias para formar las relaciones humanas."""

    def listar(
        self,
        estado: str | None = None,
        deudor_id: int | None = None,
    ) -> Sequence[Any]: ...

    def obtener(self, prestamo_id: int) -> Any | None: ...


class ConsultaParticipacionesPersona(Protocol):
    def por_inversor(self, inversor_id: int) -> Sequence[Any]: ...


class ConsultaGarantiasPersona(Protocol):
    def por_garante(self, garante_id: int) -> Sequence[Any]: ...


class ConsultaPersonasParaExportar(Protocol):
    """Lectura mínima de personas que consume la exportación CSV."""

    def listar(
        self,
        estado: str | None = None,
        rol: str | None = None,
    ) -> Sequence[Any]: ...


__all__ = [
    "RepositorioPersonas",
    "ConsultaPrestamosPersona",
    "ConsultaParticipacionesPersona",
    "ConsultaGarantiasPersona",
    "ConsultaPersonasParaExportar",
]
