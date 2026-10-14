"""Contratos públicos para la orquestación del ciclo de vida de préstamos."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ContextManager, Protocol


class ConsultaPersonasPrestamo(Protocol):
    def obtener(self, persona_id: int) -> Any | None: ...

    def roles(self, persona_id: int) -> Sequence[str]: ...

    def tiene_rol(self, persona_id: int, rol: str) -> bool: ...


class RepositorioPrestamos(Protocol):
    def crear(self, **kwargs: Any) -> int: ...

    def crear_version_tasa(self, **kwargs: Any) -> int: ...

    def guardar_tabla_amortizacion(
        self, version_id: int, tabla: list[dict]
    ) -> int: ...

    def actualizar_estado(self, prestamo_id: int, nuevo_estado: str) -> None: ...

    def obtener(self, prestamo_id: int) -> Any | None: ...

    def version_activa(self, prestamo_id: int) -> int | None: ...

    def cuotas(self, version_id: int) -> Sequence[Any]: ...


class RepositorioParticipacionesPrestamo(Protocol):
    def crear(self, **kwargs: Any) -> int: ...


class RegistroLedgerPrestamos(Protocol):
    def registrar_operacion(
        self,
        *,
        movimientos: list[dict],
        correlacion_id: str,
    ) -> Any: ...


class RegistroAuditoriaPrestamos(Protocol):
    def registrar(self, **kwargs: Any) -> int: ...


class UnidadTrabajoPrestamos(Protocol):
    """Agrupa todas las escrituras de un préstamo en una operación atómica."""

    def transaccion(self) -> ContextManager[None]: ...


__all__ = [
    "ConsultaPersonasPrestamo",
    "RepositorioPrestamos",
    "RepositorioParticipacionesPrestamo",
    "RegistroLedgerPrestamos",
    "RegistroAuditoriaPrestamos",
    "UnidadTrabajoPrestamos",
]
