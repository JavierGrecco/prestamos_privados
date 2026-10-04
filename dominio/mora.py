"""
Cálculo de mora por atraso en el pago.

La mora es un interés adicional que se cobra cuando una cuota no se
paga en fecha. Es proporcional a los días de atraso y a una tasa
pactada.

Importante: en este módulo NO se capitaliza. Es decir, la mora no
genera más mora sobre sí misma. Eso sería anatocismo, y en Argentina
está limitado por el art. 770 del CCyC. Si en algún momento se
necesita capitalizar, se hace explícitamente en otra capa y con
autorización.
"""
from datetime import date
from decimal import Decimal

from .tipos import money


def calcular_mora(
    monto_vencido: Decimal,
    tasa_mora_anual: Decimal,
    fecha_vencimiento: date,
    fecha_calculo: date,
    base_dias: int = 365,
) -> Decimal:
    """
    Calcula la mora por atraso.

    Fórmula:
        mora = monto_vencido * tasa_anual * dias_atraso / base_dias

    Parámetros:
        monto_vencido: cuánto debería haberse pagado en la fecha
            de vencimiento y no se pagó.
        tasa_mora_anual: tasa de mora (0.50 = 50% anual).
        fecha_vencimiento: cuándo vencía.
        fecha_calculo: hasta cuándo se calcula la mora.
        base_dias: 365 por defecto. Puede ser 360 según el contrato.

    Devuelve:
        La mora acumulada, redondeada a 2 decimales.

    Ejemplo:
        >>> from datetime import date
        >>> calcular_mora(
        ...     monto_vencido=Decimal("500000"),
        ...     tasa_mora_anual=Decimal("0.50"),
        ...     fecha_vencimiento=date(2026, 5, 10),
        ...     fecha_calculo=date(2026, 5, 20),
        ... )
        Decimal('6849.32')
    """
    if fecha_calculo <= fecha_vencimiento:
        return Decimal("0.00")
    if monto_vencido <= 0:
        return Decimal("0.00")
    dias = (fecha_calculo - fecha_vencimiento).days
    return money(monto_vencido * tasa_mora_anual * Decimal(dias) / Decimal(base_dias))