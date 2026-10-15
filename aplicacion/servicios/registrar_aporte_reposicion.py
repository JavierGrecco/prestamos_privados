"""Caso de uso para registrar un aporte de reposición.

La aplicación recibe la intención de registrar un aporte y delega su ejecución
en un puerto. No vuelve a calcular el equivalente USD ni duplica las
validaciones, transacciones o huellas que aplica la persistencia.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from aplicacion.puertos.registrar_aporte_reposicion import (
    RepositorioAportesReposicion,
)


class ServicioRegistrarAporteReposicion:
    """Coordina el registro sin conocer SQLite ni el repositorio concreto."""

    def __init__(self, repositorio: RepositorioAportesReposicion) -> None:
        self._repositorio = repositorio

    def registrar(
        self,
        plan_id: int,
        *,
        fecha_aporte: date,
        monto_ars: Decimal,
        cotizacion_ars_por_usd: Decimal,
        naturaleza_cotizacion: str,
        fuente_cotizacion: str,
        referencia: str,
        nota: str,
        creado_por: str,
    ) -> int:
        """Registra un aporte y devuelve el identificador de la operación.

        El repositorio sigue siendo la autoridad para validar el plan activo,
        importes, cotización, naturaleza de la fuente, fecha y operador.
        """
        return self._repositorio.registrar_aporte(
            plan_id,
            fecha_aporte=fecha_aporte,
            monto_ars=monto_ars,
            cotizacion_ars_por_usd=cotizacion_ars_por_usd,
            naturaleza_cotizacion=naturaleza_cotizacion,
            fuente_cotizacion=fuente_cotizacion,
            referencia=referencia,
            nota=nota,
            creado_por=creado_por,
        )


__all__ = ["ServicioRegistrarAporteReposicion"]
