"""Contratos de lectura usados por la vista humana de Mi espacio."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class PersonaVistaHumana:
    """Datos de identidad que la vista explica a la persona."""

    id: int
    nombre: str
    apellido: str

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()


@dataclass(frozen=True)
class PrestamoVistaHumana:
    """Datos públicos del préstamo que aparecen en Mi espacio."""

    id: int
    numero: str
    destino: str | None
    estado: str
    capital_original: Decimal


@dataclass(frozen=True)
class ParticipacionVistaHumana:
    """Parte de la inversión que corresponde a una persona."""

    prestamo_id: int
    capital_aportado: Decimal
    porcentaje: Decimal
    estado: str


class ConsultaDatosVistaHumana(Protocol):
    """Lecturas necesarias para presentar la vista humana, sin SQLite."""

    def persona_por_id(self, persona_id: int) -> PersonaVistaHumana | None: ...

    def roles_por_persona(self, persona_id: int) -> tuple[str, ...]: ...

    def prestamos_por_deudor(
        self, persona_id: int
    ) -> tuple[PrestamoVistaHumana, ...]: ...

    def prestamo_por_id(self, prestamo_id: int) -> PrestamoVistaHumana | None: ...

    def participaciones_por_inversor(
        self, persona_id: int
    ) -> tuple[ParticipacionVistaHumana, ...]: ...


__all__ = [
    "PersonaVistaHumana",
    "PrestamoVistaHumana",
    "ParticipacionVistaHumana",
    "ConsultaDatosVistaHumana",
]
