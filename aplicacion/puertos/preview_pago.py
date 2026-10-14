"""Contratos de preview para decisiones de pago Legacy.

La interfaz de consulta necesita simular la ruta histórica, pero no debe
depender de la clase concreta ni conocer cómo se ensamblan sus repositorios.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Protocol


class SimuladorPagoLegacy(Protocol):
    """Capacidad de simular una cuota o un adelanto sin persistir cambios."""

    def simular_pago(
        self,
        prestamo_id: int,
        monto: Decimal,
        fecha_calculo: date,
    ) -> dict[str, Any]: ...

    def simular_adelanto(
        self,
        prestamo_id: int,
        monto_adelanto: Decimal,
        fecha_calculo: date,
    ) -> dict[str, Any] | None: ...


__all__ = ["SimuladorPagoLegacy"]
