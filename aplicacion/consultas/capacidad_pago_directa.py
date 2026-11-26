"""Evaluación directa y explicable de una cuota con margen libre declarado.

El margen ya debe incluir gastos y obligaciones actuales. Esta consulta pura
solo descuenta la cuota nueva y el colchón opcional; no accede a personas,
repositorios, sesiones ni SQLite.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from dominio.tipos import money

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


@dataclass(frozen=True)
class EvaluacionCapacidadPagoDirecta:
    """Resultado de comparar una cuota nueva con dinero libre declarado."""

    margen_libre_declarado: Decimal
    cuota_nueva_mensual: Decimal
    colchon_mensual: Decimal
    remanente_mensual: Decimal
    porcentaje_margen_comprometido: Decimal | None


def _normalizar_importe(valor: Decimal | int | float | str, nombre: str) -> Decimal:
    try:
        importe = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{nombre} debe ser un importe válido") from exc

    if not importe.is_finite():
        raise ValueError(f"{nombre} debe ser un importe finito")

    return money(importe)


def evaluar_capacidad_pago_directa(
    *,
    margen_libre_mensual: Decimal | int | float | str,
    cuota_nueva_mensual: Decimal | int | float | str,
    colchon_mensual: Decimal | int | float | str = ZERO,
) -> EvaluacionCapacidadPagoDirecta:
    """Calcula cuánto queda luego de sumar una nueva cuota.

    El margen declarado ya debe estar neto de gastos habituales y compromisos
    actuales. No se descuentan nuevamente pagos de préstamos existentes.

    No calcula deuda/ingresos (DTI): el ingreso no forma parte de esta entrada.
    """

    margen = _normalizar_importe(margen_libre_mensual, "El margen libre")
    cuota = _normalizar_importe(cuota_nueva_mensual, "La cuota nueva")
    colchon = _normalizar_importe(colchon_mensual, "El colchón mensual")

    if cuota <= ZERO:
        raise ValueError("La cuota nueva debe ser mayor que cero")
    if colchon < ZERO:
        raise ValueError("El colchón mensual no puede ser negativo")

    remanente = money(margen - cuota - colchon)
    porcentaje = None
    if margen > ZERO:
        porcentaje = (cuota / margen * Decimal("100")).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    return EvaluacionCapacidadPagoDirecta(
        margen_libre_declarado=margen,
        cuota_nueva_mensual=cuota,
        colchon_mensual=colchon,
        remanente_mensual=remanente,
        porcentaje_margen_comprometido=porcentaje,
    )
