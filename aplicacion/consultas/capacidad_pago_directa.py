"""Evaluación directa y explicable de una cuota con margen libre declarado.

El margen ya debe incluir gastos y obligaciones actuales. Esta consulta pura
solo descuenta la cuota nueva y el colchón opcional; no accede a personas,
repositorios, sesiones ni SQLite.

El respaldo de liquidez se mantiene separado del margen mensual. Solo se
considera utilizable la reserva líquida que la persona declara disponible y
que no ha decidido proteger.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from dominio.tipos import money

ZERO = Decimal("0.00")
CENT = Decimal("0.01")
MAX_MESES_ESCENARIO = 24


@dataclass(frozen=True)
class EvaluacionRespaldoLiquidez:
    """Resultado del escenario de caja cubierto con una reserva líquida."""

    reserva_liquida_declarada: Decimal
    reserva_minima_protegida: Decimal
    reserva_utilizable: Decimal
    margen_libre_mes_ajustado: Decimal | None
    remanente_mes_ajustado: Decimal | None
    meses_escenario_ajustado: int | None
    faltante_mensual_escenario: Decimal | None
    respaldo_requerido_escenario: Decimal | None
    meses_completos_cubiertos: int | None
    respaldo_consumido_escenario: Decimal | None
    respaldo_restante_escenario: Decimal | None
    faltante_no_cubierto_escenario: Decimal | None


@dataclass(frozen=True)
class EvaluacionCapacidadPagoDirecta:
    """Resultado de comparar una cuota nueva con dinero libre declarado."""

    margen_libre_declarado: Decimal
    cuota_nueva_mensual: Decimal
    colchon_mensual: Decimal
    remanente_mensual: Decimal
    porcentaje_margen_comprometido: Decimal | None
    respaldo_liquidez: EvaluacionRespaldoLiquidez


def _normalizar_importe(
    valor: Decimal | int | float | str,
    nombre: str,
) -> Decimal:
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
    reserva_liquida_disponible: Decimal | int | float | str = ZERO,
    reserva_minima_protegida: Decimal | int | float | str = ZERO,
    margen_libre_mes_ajustado: Decimal | int | float | str | None = None,
    meses_escenario_ajustado: int = 1,
) -> EvaluacionCapacidadPagoDirecta:
    """Compara una cuota con margen habitual y, opcionalmente, con un mes difícil.

    El margen declarado ya debe estar neto de gastos y obligaciones actuales.
    No se descuentan nuevamente pagos de préstamos existentes.

    La reserva líquida no se suma al margen mensual. Solo puede cubrir el
    faltante de un escenario ajustado, sin tocar la parte protegida por la
    persona. El escenario repite el mismo margen ajustado durante la cantidad
    de meses indicada; no es un pronóstico ni una proyección contractual.

    No calcula deuda/ingresos (DTI): el ingreso no forma parte de esta entrada.
    """

    margen = _normalizar_importe(margen_libre_mensual, "El margen libre")
    cuota = _normalizar_importe(cuota_nueva_mensual, "La cuota nueva")
    colchon = _normalizar_importe(colchon_mensual, "El colchón mensual")
    reserva = _normalizar_importe(
        reserva_liquida_disponible,
        "La reserva líquida disponible",
    )
    protegida = _normalizar_importe(
        reserva_minima_protegida,
        "La reserva mínima protegida",
    )

    if cuota <= ZERO:
        raise ValueError("La cuota nueva debe ser mayor que cero")
    if colchon < ZERO:
        raise ValueError("El colchón mensual no puede ser negativo")
    if reserva < ZERO:
        raise ValueError("La reserva líquida disponible no puede ser negativa")
    if protegida < ZERO:
        raise ValueError("La reserva mínima protegida no puede ser negativa")
    remanente = money(margen - cuota - colchon)
    porcentaje = None
    if margen > ZERO:
        porcentaje = (cuota / margen * Decimal("100")).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    reserva_utilizable = money(max(ZERO, reserva - protegida))
    margen_ajustado = None
    remanente_ajustado = None
    meses_ajustados = None
    faltante_mensual = None
    respaldo_requerido = None
    meses_completos_cubiertos = None
    respaldo_consumido = None
    respaldo_restante = None
    faltante_no_cubierto = None

    if margen_libre_mes_ajustado is not None:
        margen_ajustado = _normalizar_importe(
            margen_libre_mes_ajustado,
            "El margen libre del mes ajustado",
        )
        if (
            isinstance(meses_escenario_ajustado, bool)
            or not isinstance(meses_escenario_ajustado, int)
            or not 1 <= meses_escenario_ajustado <= MAX_MESES_ESCENARIO
        ):
            raise ValueError(
                f"La duración del escenario debe estar entre 1 y {MAX_MESES_ESCENARIO} meses"
            )

        meses_ajustados = meses_escenario_ajustado
        remanente_ajustado = money(margen_ajustado - cuota - colchon)
        faltante_mensual = money(max(ZERO, -remanente_ajustado))
        respaldo_requerido = money(faltante_mensual * meses_ajustados)
        respaldo_consumido = min(reserva_utilizable, respaldo_requerido)
        respaldo_restante = money(reserva_utilizable - respaldo_consumido)
        faltante_no_cubierto = money(respaldo_requerido - respaldo_consumido)

        if faltante_mensual == ZERO:
            meses_completos_cubiertos = meses_ajustados
        else:
            meses_completos_cubiertos = min(
                meses_ajustados,
                int(reserva_utilizable // faltante_mensual),
            )

    respaldo = EvaluacionRespaldoLiquidez(
        reserva_liquida_declarada=reserva,
        reserva_minima_protegida=protegida,
        reserva_utilizable=reserva_utilizable,
        margen_libre_mes_ajustado=margen_ajustado,
        remanente_mes_ajustado=remanente_ajustado,
        meses_escenario_ajustado=meses_ajustados,
        faltante_mensual_escenario=faltante_mensual,
        respaldo_requerido_escenario=respaldo_requerido,
        meses_completos_cubiertos=meses_completos_cubiertos,
        respaldo_consumido_escenario=respaldo_consumido,
        respaldo_restante_escenario=respaldo_restante,
        faltante_no_cubierto_escenario=faltante_no_cubierto,
    )

    return EvaluacionCapacidadPagoDirecta(
        margen_libre_declarado=margen,
        cuota_nueva_mensual=cuota,
        colchon_mensual=colchon,
        remanente_mensual=remanente,
        porcentaje_margen_comprometido=porcentaje,
        respaldo_liquidez=respaldo,
    )
