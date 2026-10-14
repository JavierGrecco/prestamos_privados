"""Contratos públicos de lectura para las consultas de pago.

Las consultas de aplicación describen lo que necesitan leer. El adaptador
SQLite satisface estos protocolos sin obligar a la consulta a importar
repositorios concretos ni a conocer conexiones o filas de persistencia.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Protocol, Sequence

from dominio.politica_pago import PoliticaImputacionPago


class PrestamoLecturaPago(Protocol):
    """Campos de préstamo que consume una consulta de pago."""

    id: int | None
    numero: str
    destino: str | None
    convencion_dias: str
    sistema: str


class CuotaLecturaPago(Protocol):
    """Campos de cuota que consumen las consultas de pago de solo lectura."""

    id: int | None
    numero: int
    estado: str
    fecha_vencimiento: date | None
    cuota: Decimal
    interes: Decimal
    capital: Decimal
    saldo: Decimal
    interes_pendiente: Decimal
    capital_pendiente: Decimal
    mora_pendiente: Decimal
    tuvo_pago_parcial: bool
    fue_recalculada: bool


class DatosTasaActivaPago(Protocol):
    """Fila de datos de tasa consultada por nombre de columna."""

    def __getitem__(self, clave: str, /) -> Any: ...


class RepositorioLecturaPrestamoPago(Protocol):
    """Lecturas compartidas por las consultas de deuda y estado de cuotas."""

    def obtener(self, prestamo_id: int) -> PrestamoLecturaPago | None: ...

    def version_activa(self, prestamo_id: int) -> int | None: ...

    def info_tasa_activa(
        self, prestamo_id: int
    ) -> DatosTasaActivaPago | None: ...

    def cuotas(self, version_id: int) -> Sequence[CuotaLecturaPago]: ...


class RepositorioPoliticaPagoLectura(Protocol):
    """Consulta de la política financiera que rige en una fecha de valor."""

    def obtener_vigente(
        self,
        prestamo_id: int,
        fecha: date | None = None,
    ) -> PoliticaImputacionPago: ...


@dataclass(frozen=True, slots=True)
class ResumenPrestamoParaPago:
    """Resumen mínimo y estable que identifica el préstamo en la interfaz."""

    prestamo_id: int
    numero: str
    destino: str | None
