"""Contratos públicos de lectura para las consultas de pago.

Las consultas de aplicación describen lo que necesitan leer. El adaptador
SQLite satisface estos protocolos sin obligar a la consulta a importar
repositorios concretos ni a conocer conexiones o filas de persistencia.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Protocol, Sequence


class PrestamoLecturaPago(Protocol):
    """Campos de préstamo que consume una consulta de pago."""

    id: int | None
    numero: str
    destino: str | None
    convencion_dias: str
    sistema: str


class CuotaLecturaPago(Protocol):
    """Campos de cuota necesarios para calcular la deuda mostrada."""

    estado: str
    fecha_vencimiento: date | None
    cuota: Decimal
    interes: Decimal
    capital: Decimal
    interes_pendiente: Decimal
    capital_pendiente: Decimal
    mora_pendiente: Decimal


class DatosTasaActivaPago(Protocol):
    """Fila de datos de tasa consultada por nombre de columna."""

    def __getitem__(self, clave: str, /) -> Any: ...


class RepositorioLecturaPrestamoPago(Protocol):
    """Lecturas que necesita la consulta de deuda del próximo pago."""

    def obtener(self, prestamo_id: int) -> PrestamoLecturaPago | None: ...

    def version_activa(self, prestamo_id: int) -> int | None: ...

    def info_tasa_activa(
        self, prestamo_id: int
    ) -> DatosTasaActivaPago | None: ...

    def cuotas(self, version_id: int) -> Sequence[CuotaLecturaPago]: ...


from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResumenPrestamoParaPago:
    """Resumen mínimo y estable que identifica el préstamo en la interfaz."""

    prestamo_id: int
    numero: str
    destino: str | None
