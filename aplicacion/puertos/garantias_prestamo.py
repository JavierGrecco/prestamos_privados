"""Puertos de aplicación para constituir y finalizar garantías personales."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ContextManager, Protocol

from datetime import date
from decimal import Decimal


class ConsultaPersonaGarantia(Protocol):
    def obtener(self, persona_id: int) -> Any | None: ...

    def tiene_rol(self, persona_id: int, rol: str) -> bool: ...

    def agregar_rol(self, persona_id: int, rol: str) -> None: ...


class ConsultaPrestamoGarantia(Protocol):
    def obtener(self, prestamo_id: int) -> Any | None: ...


class RepositorioGarantiasPrestamo(Protocol):
    def por_prestamo(self, prestamo_id: int) -> Sequence[Any]: ...

    def por_garante(self, garante_id: int) -> Sequence[Any]: ...

    def activa_para_par(
        self, prestamo_id: int, garante_id: int
    ) -> Any | None: ...

    def crear(
        self,
        *,
        prestamo_id: int,
        garante_id: int,
        alcance: str,
        monto_maximo: Decimal | None,
        fecha_constitucion: date,
        creado_por: str,
    ) -> int: ...

    def obtener(self, garantia_id: int) -> Any | None: ...

    def finalizar(
        self,
        *,
        garantia_id: int,
        estado: str,
        fecha_fin: date,
        motivo: str,
    ) -> None: ...


class RegistroAuditoriaGarantias(Protocol):
    def registrar(
        self,
        *,
        usuario: str,
        operacion: str,
        entidad: str,
        entidad_id: int | None = None,
        correlacion_id: str | None = None,
        datos_anteriores: dict | None = None,
        datos_nuevos: dict | None = None,
        motivo: str | None = None,
    ) -> int: ...


class UnidadTrabajoGarantias(Protocol):
    def transaccion(
        self, *, propagar_errores_de_negocio: bool = False
    ) -> ContextManager[None]: ...


class GarantiaActivaDuplicada(Exception):
    """La pareja préstamo/garante ya tiene una garantía activa."""


__all__ = [
    "ConsultaPersonaGarantia",
    "ConsultaPrestamoGarantia",
    "RepositorioGarantiasPrestamo",
    "RegistroAuditoriaGarantias",
    "UnidadTrabajoGarantias",
    "GarantiaActivaDuplicada",
]
