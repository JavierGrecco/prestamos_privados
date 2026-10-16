"""Consulta de lectura para movimientos, valuaciones y resumen de inversión.

La consulta ordena y calcula nada por su cuenta: traduce los registros del
puerto a DTOs de pantalla y devuelve el resumen ya calculado por el repositorio.
Esto preserva las reglas de integridad, las validaciones y el XIRR existentes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from dominio.excepciones import ErrorValidacion
from aplicacion.puertos.historial_inversion_reposicion import (
    FuenteHistorialInversionReposicion,
)


@dataclass(frozen=True)
class FlujoInversionHistorial:
    """Datos del movimiento que aparecen en el historial de la interfaz."""

    id: int
    fecha_flujo: date
    tipo_flujo: str
    moneda: str
    monto_original: Decimal
    equivalente_usd: Decimal
    naturaleza_cotizacion: str
    fuente_cotizacion: str | None
    referencia: str | None


@dataclass(frozen=True)
class ValuacionInversionHistorial:
    """Datos de una valuación declarada que se presentan en pantalla."""

    id: int
    fecha_valuacion: date
    moneda: str
    valor_original: Decimal
    equivalente_usd: Decimal
    naturaleza_cotizacion: str
    fuente_cotizacion: str | None
    referencia: str | None


@dataclass(frozen=True)
class ResumenHistorialInversion:
    """Resumen financiero calculado y validado por la implementación actual."""

    cantidad_flujos: int
    cantidad_valuaciones: int
    fecha_inicio: date | None
    fecha_valuacion: date | None
    aportes_inversion_usd_ref: Decimal
    cobros_y_rescates_usd_ref: Decimal
    costos_externos_usd_ref: Decimal
    valor_mercado_final_usd_ref: Decimal | None
    resultado_total_usd_ref: Decimal | None
    xirr_anual: Decimal | None
    mensaje_xirr: str


@dataclass(frozen=True)
class HistorialInversionReposicion:
    """Todo lo que la vista necesita para representar la inversión de un plan."""

    flujos: tuple[FlujoInversionHistorial, ...]
    valuaciones: tuple[ValuacionInversionHistorial, ...]
    resumen: ResumenHistorialInversion


class ConsultaHistorialInversionReposicion:
    """Lee el historial sin exponer el repositorio concreto a la interfaz."""

    def __init__(self, fuente: FuenteHistorialInversionReposicion) -> None:
        self._fuente = fuente

    def obtener(
        self, plan_id: int, *, limite: int = 100
    ) -> HistorialInversionReposicion:
        """Devuelve el historial y su resumen respetando el orden existente."""
        if not isinstance(plan_id, int) or isinstance(plan_id, bool) or plan_id <= 0:
            raise ErrorValidacion("El identificador del plan no es válido")
        if not isinstance(limite, int) or isinstance(limite, bool) or not 1 <= limite <= 100:
            raise ErrorValidacion("El límite del historial debe estar entre 1 y 100")

        flujos = tuple(
            FlujoInversionHistorial(
                id=int(item.id),
                fecha_flujo=item.fecha_flujo,
                tipo_flujo=str(item.tipo_flujo),
                moneda=str(item.moneda),
                monto_original=item.monto_original,
                equivalente_usd=item.equivalente_usd,
                naturaleza_cotizacion=str(item.naturaleza_cotizacion),
                fuente_cotizacion=item.fuente_cotizacion,
                referencia=item.referencia,
            )
            for item in self._fuente.listar_flujos_inversion(plan_id, limite=limite)
        )
        valuaciones = tuple(
            ValuacionInversionHistorial(
                id=int(item.id),
                fecha_valuacion=item.fecha_valuacion,
                moneda=str(item.moneda),
                valor_original=item.valor_original,
                equivalente_usd=item.equivalente_usd,
                naturaleza_cotizacion=str(item.naturaleza_cotizacion),
                fuente_cotizacion=item.fuente_cotizacion,
                referencia=item.referencia,
            )
            for item in self._fuente.listar_valuaciones_inversion(
                plan_id, limite=limite
            )
        )
        resumen_fuente = self._fuente.resumen_rendimiento_inversion(plan_id)
        resumen = ResumenHistorialInversion(
            cantidad_flujos=int(resumen_fuente.cantidad_flujos),
            cantidad_valuaciones=int(resumen_fuente.cantidad_valuaciones),
            fecha_inicio=resumen_fuente.fecha_inicio,
            fecha_valuacion=resumen_fuente.fecha_valuacion,
            aportes_inversion_usd_ref=resumen_fuente.aportes_inversion_usd_ref,
            cobros_y_rescates_usd_ref=resumen_fuente.cobros_y_rescates_usd_ref,
            costos_externos_usd_ref=resumen_fuente.costos_externos_usd_ref,
            valor_mercado_final_usd_ref=resumen_fuente.valor_mercado_final_usd_ref,
            resultado_total_usd_ref=resumen_fuente.resultado_total_usd_ref,
            xirr_anual=resumen_fuente.xirr_anual,
            mensaje_xirr=str(resumen_fuente.mensaje_xirr),
        )
        return HistorialInversionReposicion(
            flujos=flujos,
            valuaciones=valuaciones,
            resumen=resumen,
        )


__all__ = [
    "ConsultaHistorialInversionReposicion",
    "FlujoInversionHistorial",
    "HistorialInversionReposicion",
    "ResumenHistorialInversion",
    "ValuacionInversionHistorial",
]
