"""
Simulador comparativo de préstamos.

NO calcula nada por su cuenta. Usa el motor de amortización y lo
ejecuta varias veces con distintos parámetros para armar tablas
comparativas.

Preguntas que responde:
  - ¿Qué pasa si en vez de 36 meses lo hago a 24?
  - ¿Y si lo estiro a 73 meses para que la cuota sea más baja?
  - ¿Cuánto más de interés pago por estirar el plazo?
"""
from datetime import date
from decimal import Decimal
from typing import Iterable

from .tipos import SistemaAmortizacion, ModalidadTasa, money
from .amortizacion import generar_tabla


def simular_plazo(
    capital: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    meses: int,
    fecha_inicio: date,
    sistema: SistemaAmortizacion = SistemaAmortizacion.FRANCES,
) -> dict:
    """
    Simula un préstamo con un plazo dado y devuelve un resumen.

    Devuelve un dict con cuota promedio, primera cuota, última cuota,
    total de intereses, total pagado y la tabla completa.
    """
    if meses <= 0:
        raise ValueError("El plazo en meses debe ser positivo")

    tabla = generar_tabla(
        capital=capital,
        tasa_anual=tasa_anual,
        modalidad=modalidad,
        meses=meses,
        fecha_inicio=fecha_inicio,
        sistema=sistema,
    )

    total_intereses = sum((f["interes"] for f in tabla), Decimal("0.00"))
    total_pagado = sum((f["cuota"] for f in tabla), Decimal("0.00"))
    cuota_promedio = money(total_pagado / Decimal(meses))
    porcentaje_interes = money(total_intereses * Decimal("100") / capital)

    return {
        "meses": meses,
        "cuota_promedio": cuota_promedio,
        "primera_cuota": tabla[0]["cuota"],
        "ultima_cuota": tabla[-1]["cuota"],
        "total_intereses": money(total_intereses),
        "total_pagado": money(total_pagado),
        "porcentaje_interes": porcentaje_interes,
        "tabla": tabla,
    }


def comparar_plazos(
    capital: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    plazos: Iterable[int],
    fecha_inicio: date,
    sistema: SistemaAmortizacion = SistemaAmortizacion.FRANCES,
) -> list[dict]:
    """
    Corre el simulador para varios plazos.

    Ejemplo: comparar 6, 8, 12, 18, 24, 30, 36, 47, 60, 73 meses.
    Los plazos impares son perfectamente válidos.
    """
    plazos_ordenados = sorted(set(plazos))
    resultados = []
    for m in plazos_ordenados:
        resultados.append(
            simular_plazo(
                capital=capital,
                tasa_anual=tasa_anual,
                modalidad=modalidad,
                meses=m,
                fecha_inicio=fecha_inicio,
                sistema=sistema,
            )
        )
    return resultados


def simular_tasas(
    capital: Decimal,
    modalidad: ModalidadTasa,
    meses: int,
    tasas: Iterable[Decimal],
    fecha_inicio: date,
    sistema: SistemaAmortizacion = SistemaAmortizacion.FRANCES,
) -> list[dict]:
    """Igual que comparar_plazos pero variando la tasa."""
    resultados = []
    for t in sorted(set(tasas)):
        r = simular_plazo(
            capital=capital,
            tasa_anual=t,
            modalidad=modalidad,
            meses=meses,
            fecha_inicio=fecha_inicio,
            sistema=sistema,
        )
        r["tasa"] = t
        resultados.append(r)
    return resultados