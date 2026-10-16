"""Caso de uso para registrar un movimiento declarado de inversión.

Este servicio coordina la solicitud de registro, pero no recalcula rendimiento
ni equivale movimientos de inversión a aportes de reposición. El repositorio
sigue siendo responsable de las reglas financieras, la transacción y la huella.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from aplicacion.puertos.registrar_flujo_inversion import (
    RepositorioFlujosInversion,
)


class ServicioRegistrarFlujoInversion:
    """Coordina el registro de un flujo mediante un puerto de aplicación."""

    def __init__(self, repositorio: RepositorioFlujosInversion) -> None:
        self._repositorio = repositorio

    def registrar(
        self,
        plan_id: int,
        *,
        fecha_flujo: date,
        tipo_flujo: str,
        moneda: str,
        monto_original: Decimal,
        cotizacion_ars_por_usd: Decimal | None = None,
        naturaleza_cotizacion: str | None = None,
        fuente_cotizacion: str = "",
        referencia: str = "",
        nota: str = "",
        creado_por: str,
    ) -> int:
        """Registra el movimiento delegando las validaciones al repositorio."""
        return self._repositorio.registrar_flujo_inversion(
            plan_id,
            fecha_flujo=fecha_flujo,
            tipo_flujo=tipo_flujo,
            moneda=moneda,
            monto_original=monto_original,
            cotizacion_ars_por_usd=cotizacion_ars_por_usd,
            naturaleza_cotizacion=naturaleza_cotizacion,
            fuente_cotizacion=fuente_cotizacion,
            referencia=referencia,
            nota=nota,
            creado_por=creado_por,
        )


__all__ = ["ServicioRegistrarFlujoInversion"]
