"""
Análisis de paridad cambiaria.

Responde a la pregunta central del sistema: ¿realmente gané o perdí?
No en pesos nominales, sino en poder de compra medido en una moneda
más estable como el dólar.

Este módulo calcula:
  - Rendimiento nominal en USD (ajustando el rendimiento en ARS por
    la variación del tipo de cambio).
  - Rendimiento real (ajustado por inflación, tanto de Argentina
    como de EE.UU.).
  - Costo equivalente del deudor en USD.
  - Tipo de cambio de paridad: el TC que igualaría los costos.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .tipos import money


@dataclass
class PuntoParidad:
    """Un punto en la serie histórica de paridad cambiaria."""
    fecha: date
    tc: Decimal
    saldo_capital_ars: Decimal
    saldo_capital_usd: Decimal


@dataclass
class AnalisisParidad:
    """Resultado completo del análisis."""
    puntos: list[PuntoParidad]
    tc_inicial: Decimal
    tc_final: Decimal
    variacion_tc_pct: Decimal
    rendimiento_nominal_ars: Decimal
    rendimiento_nominal_usd: Decimal
    rendimiento_real_usd: Decimal | None
    rendimiento_real_ars: Decimal | None
    costo_deudor_ars: Decimal
    costo_deudor_usd_equivalente: Decimal
    diferencia_costo_pct: Decimal
    tc_paridad: Decimal


def calcular_rendimiento_usd(
    rendimiento_ars: Decimal,
    tc_inicio: Decimal,
    tc_fin: Decimal,
) -> Decimal:
    """
    Convierte un rendimiento en ARS a su equivalente en USD.

    Fórmula:
        r_usd = (1 + r_ars) * (tc_inicio / tc_fin) - 1

    Ejemplo:
        Si el rendimiento en ARS fue del 50% y el dólar subió
        de 100 a 150, el rendimiento en USD es:
        (1.50) * (100/150) - 1 = 0. Es decir, empataste.
    """
    factor_tc = tc_inicio / tc_fin
    return money((Decimal("1") + rendimiento_ars) * factor_tc - Decimal("1"))


def calcular_rendimiento_real(
    rendimiento_nominal: Decimal,
    inflacion_acumulada: Decimal,
) -> Decimal:
    """
    Calcula el rendimiento real usando la ecuación de Fisher.

    Fórmula:
        r_real = (1 + r_nominal) / (1 + inflacion) - 1

    Ejemplo:
        Si el rendimiento nominal fue del 50% y la inflación
        acumulada fue del 60%, el rendimiento real es:
        (1.50 / 1.60) - 1 = -0.0625. Es decir, perdiste 6.25%
        de poder de compra.
    """
    if inflacion_acumulada <= -1:
        raise ValueError("La inflación no puede ser -100% o menor")
    return money(
        (Decimal("1") + rendimiento_nominal)
        / (Decimal("1") + inflacion_acumulada)
        - Decimal("1")
    )


def calcular_costo_equivalente_usd(pagos: list[dict]) -> Decimal:
    """
    Calcula cuánto habría costado el préstamo si los pagos se
    hubieran hecho en dólares, usando el TC de cada fecha.

    Cada pago debe tener: monto_ars y tc_usd.
    """
    total_usd = Decimal("0.00")
    for pago in pagos:
        if pago["tc_usd"] > 0:
            total_usd += pago["monto_ars"] / pago["tc_usd"]
    return money(total_usd)


def calcular_tc_paridad(
    total_pagado_ars: Decimal,
    total_pagado_usd: Decimal,
) -> Decimal:
    """
    Calcula el TC que igualaría los costos en ARS y USD.

    Si el TC final real es mayor al de paridad, el deudor en ARS
    pagó menos (en USD) de lo que habría pagado en USD. Si es menor,
    pagó más.
    """
    if total_pagado_usd == 0:
        raise ValueError("El total pagado en USD no puede ser cero")
    return money(total_pagado_ars / total_pagado_usd)