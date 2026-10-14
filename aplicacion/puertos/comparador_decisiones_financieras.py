"""Contratos de lectura que necesita el comparador M7."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class PrestamoComparadorLectura:
    """Condiciones registradas que el comparador muestra por alternativa."""

    id: int
    numero: str
    destino: str | None
    estado: str
    capital_original: Decimal
    moneda_contractual: str
    sistema: str
    convencion_dias: str
    fecha_inicio: date | None


@dataclass(frozen=True)
class ParticipacionComparadorLectura:
    """Capital y estado de una participación vinculada a un inversor."""

    prestamo_id: int
    estado: str
    capital_aportado: Decimal
    porcentaje: Decimal


@dataclass(frozen=True)
class TasaActivaComparadorLectura:
    """Tasa y modalidad vigentes registradas para un préstamo."""

    tasa_anual: Decimal
    modalidad: str


class ConsultaDatosComparadorDecisiones(Protocol):
    """Lectura tipada para descubrir alternativas y sus condiciones."""

    def persona_existe(self, persona_id: int) -> bool: ...

    def prestamos_por_deudor(
        self, persona_id: int
    ) -> tuple[PrestamoComparadorLectura, ...]: ...

    def participaciones_por_inversor(
        self, persona_id: int
    ) -> tuple[ParticipacionComparadorLectura, ...]: ...

    def prestamo_por_id(
        self, prestamo_id: int
    ) -> PrestamoComparadorLectura | None: ...

    def tasa_activa(
        self, prestamo_id: int
    ) -> TasaActivaComparadorLectura | None: ...


__all__ = [
    "PrestamoComparadorLectura",
    "ParticipacionComparadorLectura",
    "TasaActivaComparadorLectura",
    "ConsultaDatosComparadorDecisiones",
]
