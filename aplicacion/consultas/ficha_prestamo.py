"""Consulta de lectura para la ficha básica de un préstamo.

Agrupa los datos persistidos que necesita la pantalla de detalle. No calcula
intereses, no decide estados ni modifica préstamos o pagos.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class PrestamoFicha:
    """Datos del préstamo necesarios para presentar la ficha y sus garantías."""

    id: int
    numero: str
    deudor_id: int | None
    capital_original: Decimal
    plazo_meses: int
    sistema: str
    fecha_inicio: date | None
    estado: str
    destino: str | None


@dataclass(frozen=True)
class TasaActivaFicha:
    """Tasa guardada en la versión vigente, sin reinterpretarla."""

    tasa_anual: Decimal
    modalidad_tasa: str


@dataclass(frozen=True)
class PagoFicha:
    """Campos de un pago usados en el resumen visible del detalle."""

    estado: str
    fecha_real: date | None
    monto_moneda_pago: Decimal
    tipo_pago: str
    medio: str | None
    nota: str | None


@dataclass(frozen=True)
class FichaPrestamo:
    """Snapshot de lectura que consume la pantalla de detalle."""

    prestamo: PrestamoFicha
    tasa_activa: TasaActivaFicha | None
    pagos_validos: tuple[PagoFicha, ...]


class FuenteFichaPrestamo(Protocol):
    """Contrato de lectura; la UI no necesita conocer repositorios ni SQL."""

    def obtener_prestamo(self, prestamo_id: int) -> PrestamoFicha | None:
        """Busca el préstamo por su identificador."""

    def obtener_tasa_activa(
        self, prestamo_id: int
    ) -> TasaActivaFicha | None:
        """Lee la tasa de la versión activa, si existe."""

    def listar_pagos(self, prestamo_id: int) -> tuple[PagoFicha, ...]:
        """Lista los pagos en el orden histórico de la consulta de persistencia."""


class ConsultaFichaPrestamo:
    """Prepara únicamente los datos de lectura que muestra la ficha."""

    def __init__(self, fuente: FuenteFichaPrestamo) -> None:
        self._fuente = fuente

    def obtener(self, prestamo_id: int) -> FichaPrestamo | None:
        """Devuelve la ficha o None si el préstamo no existe.

        Se conservan el orden de pagos definido por el repositorio, la tasa de
        la versión activa y el filtro histórico de pagos con estado VALIDA.
        """
        prestamo = self._fuente.obtener_prestamo(prestamo_id)
        if prestamo is None:
            return None

        tasa = self._fuente.obtener_tasa_activa(prestamo_id)
        pagos = self._fuente.listar_pagos(prestamo_id)
        pagos_validos = tuple(pago for pago in pagos if pago.estado == "VALIDA")

        return FichaPrestamo(
            prestamo=prestamo,
            tasa_activa=tasa,
            pagos_validos=pagos_validos,
        )


__all__ = [
    "ConsultaFichaPrestamo",
    "FichaPrestamo",
    "FuenteFichaPrestamo",
    "PagoFicha",
    "PrestamoFicha",
    "TasaActivaFicha",
]
