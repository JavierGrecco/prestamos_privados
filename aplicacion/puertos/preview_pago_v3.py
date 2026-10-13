"""Contratos de lectura que necesita la consulta de preview V3.

Estos puertos describen consultas de solo lectura. Sus implementaciones pueden
usar SQLite, pero el servicio de aplicación no construye repositorios concretos.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, Mapping

from aplicacion.puertos.consulta_prestamo_pago import RepositorioLecturaPrestamoPago
from aplicacion.puertos.registro_pago_v3 import EstadoRegistroPagoV3
from dominio.adelanto_v3 import CuotaFuturaAdelantoV3
from dominio.politica_pago import PoliticaImputacionPago


class RepositorioPoliticaPreviewV3(Protocol):
    """Consulta de política de pago vigente e historial de versiones."""

    def obtener_vigente_con_id(
        self, prestamo_id: int, fecha: date | None = None
    ) -> tuple[int, PoliticaImputacionPago]: ...

    def version_por_id(self, politica_id: int) -> int: ...


class RepositorioEstadoPreviewPagoV3(Protocol):
    """Lecturas V3 necesarias para calcular el preview sin persistir."""

    def obtener_estado_pago(self, prestamo_id: int) -> EstadoRegistroPagoV3: ...

    def ultimo_hasta_interes_capital_por_cuotas(
        self, prestamo_id: int, cuota_ids: tuple[int, ...]
    ) -> Mapping[int, date]: ...

    def ultimo_hasta_mora_contractual_por_cuotas(
        self, prestamo_id: int, cuota_ids: tuple[int, ...]
    ) -> Mapping[int, date]: ...

    def cuotas_futuras_para_adelanto(
        self, prestamo_id: int, numero_desde: int
    ) -> tuple[CuotaFuturaAdelantoV3, ...]: ...


__all__ = [
    "RepositorioLecturaPrestamoPago",
    "RepositorioPoliticaPreviewV3",
    "RepositorioEstadoPreviewPagoV3",
]
