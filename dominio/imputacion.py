"""
Waterfall de imputación de pagos.

Cuando alguien paga, ese dinero puede cubrir varios conceptos:
gastos, penalizaciones, mora, interés, capital. La pregunta es:
¿en qué orden se aplica?

Este módulo implementa el "waterfall" (cascada): el pago se aplica
al primer concepto de la lista, después al siguiente, y así hasta
agotarse. Lo que sobra queda como excedente.

El orden es configurable por préstamo. Por defecto es:
    gasto → penalización → mora → interés → capital

La invariante que siempre se cumple:
    suma(aplicado) + excedente = monto del pago
"""
from decimal import Decimal
from typing import Mapping

from .tipos import ConceptoImputacion, ORDEN_DEFAULT_IMPUTACION, money
from .excepciones import ErrorValidacion, ErrorInvariante


def imputar_pago(
    monto: Decimal,
    deudas: Mapping[ConceptoImputacion, Decimal],
    orden: list[ConceptoImputacion] | None = None,
) -> tuple[dict[ConceptoImputacion, Decimal], Decimal]:
    """
    Reparte un pago entre las deudas pendientes siguiendo un orden.

    Parámetros:
        monto: dinero recibido. No puede ser negativo.
        deudas: cuánto se debe por cada concepto. Ejemplo:
            {
                ConceptoImputacion.INTERES: Decimal("500000"),
                ConceptoImputacion.CAPITAL: Decimal("349032"),
            }
        orden: orden de prioridad. Si no se pasa, usa el orden
            por defecto (gasto → penalización → mora → interés → capital).

    Devuelve:
        Una tupla con dos elementos:
        - aplicado: dict con el monto aplicado a cada concepto.
        - excedente: lo que sobró después de cubrir todas las deudas.
          Si el pago fue menor a la deuda total, es 0.
          Si fue mayor, queda como saldo a favor.

    Ejemplo:
        >>> deudas = {ConceptoImputacion.INTERES: Decimal("500000")}
        >>> aplicado, excedente = imputar_pago(Decimal("300000"), deudas)
        >>> aplicado[ConceptoImputacion.INTERES]
        Decimal('300000.00')
        >>> excedente
        Decimal('0.00')
    """
    if monto < 0:
        raise ErrorValidacion("El monto del pago no puede ser negativo")

    orden = orden or ORDEN_DEFAULT_IMPUTACION
    resto = money(monto)
    aplicado = {c: Decimal("0.00") for c in ConceptoImputacion}

    for concepto in orden:
        if resto <= Decimal("0.00"):
            break
        deuda = money(deudas.get(concepto, Decimal("0.00")))
        if deuda <= Decimal("0.00"):
            continue
        aplica = min(resto, deuda)
        aplicado[concepto] = money(aplica)
        resto = money(resto - aplica)

    # Verificación de invariante. Si esto falla, hay un bug.
    total_aplicado = sum(aplicado.values(), Decimal("0.00"))
    if money(total_aplicado + resto) != money(monto):
        raise ErrorInvariante(
            f"La suma de lo aplicado ({total_aplicado}) más el excedente "
            f"({resto}) no coincide con el monto recibido ({monto})."
        )

    return aplicado, money(resto)