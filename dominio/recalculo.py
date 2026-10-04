"""
Motor de recálculo de tablas de amortización.

Cuando el deudor adelanta capital, hay dos formas de recalcular:

  - RAI (Reducir el monto de cada cuota): mantiene el plazo original
    y baja el monto de las cuotas restantes.
  - RNI (Reducir el número de cuotas): mantiene la cuota original
    y acorta el plazo.

Este módulo es puro: no toca base de datos ni UI. Solo matemática.
"""
import math
from datetime import date
from decimal import Decimal, ROUND_CEILING

from dateutil.relativedelta import relativedelta

from .amortizacion import generar_tabla
from .interes import tasa_mensual
from .tipos import (
    ModalidadTasa,
    SistemaAmortizacion,
    money,
)


def recalcular_rai(
    capital_pendiente: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    meses_restantes: int,
    fecha_ultimo_vencimiento: date,
    sistema: SistemaAmortizacion = SistemaAmortizacion.FRANCES,
) -> list[dict]:
    """
    Recalcula la tabla manteniendo el plazo original (RAI).

    El capital pendiente es menor, entonces las cuotas bajan
    de monto. La cantidad de cuotas es la misma que quedaba.

    Parámetros:
        capital_pendiente: capital que falta pagar.
        tasa_anual: tasa del préstamo.
        modalidad: TNA o TEA.
        meses_restantes: cuántas cuotas quedaban.
        fecha_ultimo_vencimiento: fecha de la última cuota original.
            Se usa para calcular hacia atrás la fecha de inicio
            del recálculo.
        sistema: sistema de amortización.

    Devuelve la nueva tabla con el mismo formato que generar_tabla.
    """
    fecha_inicio_recalculo = fecha_ultimo_vencimiento - relativedelta(
        months=meses_restantes
    )
    return generar_tabla(
        capital=capital_pendiente,
        tasa_anual=tasa_anual,
        modalidad=modalidad,
        meses=meses_restantes,
        fecha_inicio=fecha_inicio_recalculo,
        sistema=sistema,
    )


def recalcular_rni(
    capital_pendiente: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    cuota_objetivo: Decimal,
    fecha_ultimo_vencimiento: date,
    sistema: SistemaAmortizacion = SistemaAmortizacion.FRANCES,
) -> tuple[list[dict], int] | tuple[None, None]:
    """
    Recalcula la tabla manteniendo la cuota original (RNI).

    El capital pendiente es menor, entonces la cantidad de cuotas
    necesarias también es menor. El préstamo termina antes.

    Devuelve (tabla, cantidad_cuotas). Si la cuota no alcanza para
    cubrir los intereses del capital pendiente, devuelve (None, None).
    """
    i = tasa_mensual(tasa_anual, modalidad)

    if i == 0:
        # Sin interés: cuotas = capital / cuota
        n = int(
            (capital_pendiente / cuota_objetivo).to_integral_value(
                rounding=ROUND_CEILING
            )
        )
    else:
        # Fórmula: n = -log(1 - P*i/C) / log(1+i)
        try:
            num = 1 - float(capital_pendiente) * float(i) / float(cuota_objetivo)
        except (ValueError, ZeroDivisionError):
            return None, None

        if num <= 0:
            # La cuota no alcanza para pagar ni los intereses
            return None, None

        n = math.ceil(-math.log(num) / math.log(1 + float(i)))

    if n <= 0:
        return None, None

    fecha_inicio_recalculo = fecha_ultimo_vencimiento - relativedelta(months=n)

    tabla = generar_tabla(
        capital=capital_pendiente,
        tasa_anual=tasa_anual,
        modalidad=modalidad,
        meses=n,
        fecha_inicio=fecha_inicio_recalculo,
        sistema=sistema,
    )
    return tabla, n


def calcular_impacto(
    tabla_actual_restante: list[dict],
    tabla_nueva: list[dict],
) -> dict:
    """
    Calcula el impacto del recálculo comparando las dos tablas.

    Devuelve:
        - intereses_antes: intereses que se iban a pagar.
        - intereses_despues: intereses que se van a pagar.
        - ahorro: diferencia.
        - meses_antes: cuántas cuotas quedaban.
        - meses_despues: cuántas quedan.
        - meses_ahorrados: diferencia.
        - cuota_promedio_antes: promedio de las cuotas originales.
        - cuota_promedio_despues: promedio de las cuotas nuevas.
    """
    def suma_intereses(tabla):
        return sum((f["interes"] for f in tabla), Decimal("0.00"))

    def suma_cuotas(tabla):
        return sum((f["cuota"] for f in tabla), Decimal("0.00"))

    meses_antes = len(tabla_actual_restante)
    meses_despues = len(tabla_nueva)

    intereses_antes = suma_intereses(tabla_actual_restante)
    intereses_despues = suma_intereses(tabla_nueva)

    cuota_prom_antes = (
        money(suma_cuotas(tabla_actual_restante) / Decimal(meses_antes))
        if meses_antes > 0 else Decimal("0.00")
    )
    cuota_prom_despues = (
        money(suma_cuotas(tabla_nueva) / Decimal(meses_despues))
        if meses_despues > 0 else Decimal("0.00")
    )

    return {
        "intereses_antes": intereses_antes,
        "intereses_despues": intereses_despues,
        "ahorro": intereses_antes - intereses_despues,
        "meses_antes": meses_antes,
        "meses_despues": meses_despues,
        "meses_ahorrados": meses_antes - meses_despues,
        "cuota_promedio_antes": cuota_prom_antes,
        "cuota_promedio_despues": cuota_prom_despues,
    }