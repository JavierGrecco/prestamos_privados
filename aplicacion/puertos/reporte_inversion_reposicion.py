"""Contrato de lectura para informes de reposición e inversión interna.

Los tipos describen los datos que el informe presenta. El puerto no conoce
SQLite ni depende de modelos concretos del repositorio.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Protocol, Sequence


TipoConteoReporteReposicion = Literal["aportes", "flujos", "valuaciones"]


class PlanReposicionLectura(Protocol):
    id: int
    nombre: str
    tipo_plan: str
    fecha_desembolso: date
    capital_original_ars: Decimal
    estado: str
    creado_por: str
    ultima_version: int


class VersionPlanReposicionLectura(Protocol):
    id: int
    plan_id: int
    numero_version: int
    nombre: str
    tipo_plan: str
    fecha_desembolso: date
    capital_original_ars: Decimal
    snapshot_sha256: str
    snapshot_json: str | None


class AporteReposicionLectura(Protocol):
    id: int
    plan_id: int
    fecha_aporte: date
    monto_ars: Decimal
    cotizacion_ars_por_usd: Decimal
    equivalente_usd: Decimal
    naturaleza_cotizacion: str
    fuente_cotizacion: str | None
    referencia: str | None
    nota: str | None
    snapshot_sha256: str
    creado_por: str
    creado_en: str


class FlujoInversionReposicionLectura(Protocol):
    id: int
    plan_id: int
    fecha_flujo: date
    tipo_flujo: str
    moneda: str
    monto_original: Decimal
    cotizacion_ars_por_usd: Decimal | None
    equivalente_usd: Decimal
    naturaleza_cotizacion: str
    fuente_cotizacion: str | None
    referencia: str | None
    nota: str | None
    snapshot_sha256: str
    creado_por: str
    creado_en: str


class ValoracionInversionReposicionLectura(Protocol):
    id: int
    plan_id: int
    fecha_valuacion: date
    moneda: str
    valor_original: Decimal
    cotizacion_ars_por_usd: Decimal | None
    equivalente_usd: Decimal
    naturaleza_cotizacion: str
    fuente_cotizacion: str | None
    referencia: str | None
    nota: str | None
    snapshot_sha256: str
    creado_por: str
    creado_en: str


class ResumenRendimientoInversionLectura(Protocol):
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


class ConsultaReporteInversionReposicion(Protocol):
    """Lecturas ya verificadas para construir el informe exportable."""

    def obtener_plan(self, plan_id: int) -> PlanReposicionLectura | None: ...

    def obtener_version(
        self, plan_id: int, numero_version: int
    ) -> VersionPlanReposicionLectura | None: ...

    def verificar_version(self, version: VersionPlanReposicionLectura) -> bool: ...

    def contar_registros(
        self, tipo: TipoConteoReporteReposicion, plan_id: int
    ) -> int: ...

    def listar_aportes(
        self, plan_id: int, limite: int
    ) -> Sequence[AporteReposicionLectura]: ...

    def obtener_aporte(self, aporte_id: int) -> AporteReposicionLectura | None: ...

    def verificar_aporte(self, aporte: AporteReposicionLectura) -> bool: ...

    def listar_flujos_inversion(
        self, plan_id: int, limite: int
    ) -> Sequence[FlujoInversionReposicionLectura]: ...

    def listar_valuaciones_inversion(
        self, plan_id: int, limite: int
    ) -> Sequence[ValoracionInversionReposicionLectura]: ...

    def resumen_rendimiento_inversion(
        self, plan_id: int
    ) -> ResumenRendimientoInversionLectura: ...


__all__ = [
    "TipoConteoReporteReposicion",
    "PlanReposicionLectura",
    "VersionPlanReposicionLectura",
    "AporteReposicionLectura",
    "FlujoInversionReposicionLectura",
    "ValoracionInversionReposicionLectura",
    "ResumenRendimientoInversionLectura",
    "ConsultaReporteInversionReposicion",
]
