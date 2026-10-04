"""
Análisis de licuación por inflación.

La licuación es el fenómeno por el cual el valor real de una deuda
o cuota disminuye cuando la inflación supera a la tasa de interés.

Ejemplo: si tenés una cuota fija de $850.000 y la inflación es del
5% mensual, después de 12 meses esa cuota vale en términos reales
$850.000 / 1.05^12 = $473.000. Es decir, se licuó un 44%.

Este módulo calcula eso de forma explícita, para que el usuario
pueda ver cuánto se está licuando su cuota o su deuda.
"""
from decimal import Decimal

from .tipos import money


def factor_inflacion_acumulada(
    inflacion_mensual: Decimal,
    meses: int,
) -> Decimal:
    """
    Factor por el que hay que dividir un valor nominal para obtener
    su equivalente en pesos del mes 0.

    Ejemplo: con 5% mensual durante 12 meses → 1.05^12 ≈ 1.796.
    """
    return (Decimal("1") + inflacion_mensual) ** meses


def valor_real(
    valor_nominal: Decimal,
    inflacion_mensual: Decimal,
    meses: int,
) -> Decimal:
    """
    Convierte un valor nominal futuro a su equivalente en pesos de hoy.

    Ejemplo:
        >>> valor_real(Decimal("850000"), Decimal("0.05"), 12)
        Decimal('473086.13')
    """
    factor = factor_inflacion_acumulada(inflacion_mensual, meses)
    return money(valor_nominal / factor)


def proyectar_licuacion(
    cuota_nominal: Decimal,
    inflacion_mensual: Decimal,
    meses: int,
) -> list[dict]:
    """
    Proyecta el valor real de una cuota mes a mes.

    Devuelve una lista de dicts con:
        mes: número de mes.
        cuota_nominal: la cuota en pesos nominales (constante).
        cuota_real: la cuota en pesos del mes 0.
        licuacion_acumulada: qué porcentaje del valor original
            se perdió por inflación hasta este mes.
    """
    resultado = []
    factor = Decimal("1")
    for mes in range(1, meses + 1):
        factor *= (Decimal("1") + inflacion_mensual)
        cuota_real = money(cuota_nominal / factor)
        licuacion = money(Decimal("1") - (cuota_real / cuota_nominal))
        resultado.append({
            "mes": mes,
            "cuota_nominal": money(cuota_nominal),
            "cuota_real": cuota_real,
            "licuacion_acumulada": licuacion,
        })
    return resultado


def calcular_tasa_real(
    tasa_nominal: Decimal,
    inflacion_acumulada: Decimal,
) -> Decimal:
    """
    Calcula la tasa real (ecuación de Fisher).

    r_real = (1 + r_nominal) / (1 + inflacion) - 1

    Si es negativa, la inflación le gana a la tasa y el deudor se
    beneficia porque paga con pesos que valen menos.
    """
    return money(
        (Decimal("1") + tasa_nominal) / (Decimal("1") + inflacion_acumulada)
        - Decimal("1")
    )