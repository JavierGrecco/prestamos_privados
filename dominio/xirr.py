"""
XIRR: Tasa Interna de Retorno con fechas irregulares.

¿Qué es? Es la tasa anualizada que hace que el valor presente neto
de todos los flujos de caja sea exactamente cero. Se usa para medir
el rendimiento real de una inversión cuando los flujos no son
periódicos (por ejemplo, cuando cobrás cuotas con fechas que varían).

La diferencia con TIR común es que XIRR usa fechas reales, no
períodos fijos. Es lo que usa Excel en la función XIRR.

Convención de signos:
  - Aportes (dinero que sale del inversor): NEGATIVO
  - Cobros (dinero que entra al inversor): POSITIVO

Método: Newton-Raphson, que converge rápido en la mayoría de los
casos. Si no converge, se levanta un error.
"""
from datetime import date
from decimal import Decimal

from .excepciones import ErrorCalculo, ErrorValidacion


def xirr(
    flujos: list[tuple[date, Decimal]],
    guess: float = 0.1,
    tolerancia: float = 1e-9,
    max_iter: int = 200,
) -> Decimal:
    """
    Calcula la XIRR para una serie de flujos con fechas irregulares.

    Parámetros:
        flujos: lista de (fecha, monto). Los montos que salen del
            inversor van en negativo, los que entran en positivo.
        guess: valor inicial para el método iterativo. 0.1 (10%)
            funciona bien en la mayoría de los casos.
        tolerancia: qué tan preciso debe ser el resultado.
        max_iter: máximo de iteraciones antes de rendirse.

    Devuelve:
        La tasa anualizada como Decimal (0.35 = 35%).

    Errores:
        ErrorValidacion: si hay menos de 2 flujos, o si todos los
            flujos tienen el mismo signo (no hay nada que resolver).
        ErrorCalculo: si el método no converge.

    Ejemplo:
        >>> from datetime import date
        >>> xirr([
        ...     (date(2026, 1, 1), Decimal("-1000")),
        ...     (date(2027, 1, 1), Decimal("1100")),
        ... ])
        Decimal('0.10000000')
    """
    if len(flujos) < 2:
        raise ErrorValidacion("XIRR requiere al menos 2 flujos")

    flujos_ord = sorted(flujos, key=lambda x: x[0])
    tiene_neg = any(m < 0 for _, m in flujos_ord)
    tiene_pos = any(m > 0 for _, m in flujos_ord)
    if not (tiene_neg and tiene_pos):
        raise ErrorValidacion(
            "XIRR necesita al menos un flujo negativo y uno positivo"
        )

    d0 = flujos_ord[0][0]

    def npv(r: float) -> float:
        """Valor presente neto a una tasa dada."""
        total = 0.0
        for fecha, monto in flujos_ord:
            t = (fecha - d0).days / 365.0
            total += float(monto) / ((1.0 + r) ** t)
        return total

    def d_npv(r: float) -> float:
        """Derivada del NPV respecto a la tasa."""
        total = 0.0
        for fecha, monto in flujos_ord:
            t = (fecha - d0).days / 365.0
            if t == 0:
                continue
            total -= t * float(monto) / ((1.0 + r) ** (t + 1.0))
        return total

    r = guess
    for _ in range(max_iter):
        f = npv(r)
        df = d_npv(r)
        if abs(df) < 1e-15:
            break
        nuevo = r - f / df
        if abs(nuevo - r) < tolerancia:
            r = nuevo
            break
        r = nuevo

    if abs(npv(r)) > 1.0:
        raise ErrorCalculo(
            f"XIRR no convergió. El NPV final es {npv(r):.4f}. "
            "Probablemente los flujos no tienen solución real."
        )

    return Decimal(str(r)).quantize(Decimal("0.00000001"))