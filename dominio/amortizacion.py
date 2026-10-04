"""
Generación de tablas de amortización.

Este es el corazón del motor financiero. Dado un capital, una tasa,
un plazo y un sistema, genera la lista de cuotas con su desglose.

La regla fundamental: la última cuota se ajusta para que el saldo
final sea EXACTAMENTE cero. Esto es necesario porque el redondeo a
centavos deja pequeñas diferencias que se acumulan. En lugar de
arrastrar centavos, se ajusta la última cuota y se registra el ajuste.
"""
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from .tipos import SistemaAmortizacion, ModalidadTasa, money
from .interes import tasa_mensual
from .excepciones import ErrorValidacion, ErrorInvariante


def _sumar_meses(fecha: date, meses: int) -> date:
    """
    Suma meses a una fecha manejando correctamente fin de mes.

    Si hoy es 31 de enero y sumás 1 mes, el resultado es 28 o 29
    de febrero (según bisiesto), no 3 de marzo. Esto es lo que
    hace relativedelta y es lo esperado en finanzas.
    """
    return fecha + relativedelta(months=meses)


def cuota_francesa(
    capital: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    meses: int,
) -> Decimal:
    """
    Calcula la cuota fija del sistema francés.

    Fórmula:
        C = P * i / (1 - (1 + i)^(-n))

    Donde P es el capital, i la tasa del período y n el número de
    períodos. Cuando la tasa es cero, la fórmula se indetermina,
    así que se maneja como caso especial: C = P / n.

    Ejemplo:
        >>> cuota_francesa(Decimal("20000000"), Decimal("0.30"),
        ...                ModalidadTasa.TNA, 36)
        Decimal('849029.68')  # Aproximadamente 849 mil pesos
    """
    if capital <= 0 or meses <= 0:
        raise ErrorValidacion("Capital y meses deben ser positivos")

    i = tasa_mensual(tasa_anual, modalidad)
    if i == 0:
        return money(capital / Decimal(meses))

    factor = (1 + i) ** (-meses)
    return money(capital * i / (1 - factor))


def generar_tabla(
    capital: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    meses: int,
    fecha_inicio: date,
    sistema: SistemaAmortizacion,
    meses_interes_only: int = 0,
) -> list[dict]:
    """
    Genera la tabla de amortización completa.

    Devuelve una lista de diccionarios, uno por cuota. Cada uno tiene:
        numero: número de cuota (1, 2, 3...)
        vencimiento: fecha de vencimiento.
        capital_inicial: saldo antes de esta cuota.
        interes: interés de esta cuota.
        capital: amortización de capital de esta cuota.
        cuota: monto total a pagar.
        saldo: saldo después de esta cuota.

    La última cuota se ajusta para que el saldo final sea cero exacto.

    Parámetros:
        meses_interes_only: solo aplica al sistema INTERES_ONLY.
            Indica cuántos meses iniciales son de solo interés.

    Ejemplo:
        >>> from datetime import date
        >>> tabla = generar_tabla(
        ...     capital=Decimal("1000000"),
        ...     tasa_anual=Decimal("0.30"),
        ...     modalidad=ModalidadTasa.TNA,
        ...     meses=12,
        ...     fecha_inicio=date(2026, 1, 1),
        ...     sistema=SistemaAmortizacion.FRANCES,
        ... )
        >>> len(tabla)
        12
        >>> tabla[-1]["saldo"]
        Decimal('0.00')
    """
    if sistema == SistemaAmortizacion.FRANCES:
        return _tabla_francesa(capital, tasa_anual, modalidad, meses, fecha_inicio)
    if sistema == SistemaAmortizacion.ALEMAN:
        return _tabla_alemana(capital, tasa_anual, modalidad, meses, fecha_inicio)
    if sistema == SistemaAmortizacion.INTERES_ONLY:
        return _tabla_interes_only(
            capital, tasa_anual, modalidad, meses, fecha_inicio, meses_interes_only
        )
    raise ErrorValidacion(f"Sistema de amortización no soportado: {sistema}")


def _tabla_francesa(
    capital: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    meses: int,
    fecha_inicio: date,
) -> list[dict]:
    """
    Tabla del sistema francés. La cuota es (casi) constante. Al
    principio se paga más interés y menos capital; al final, al revés.
    """
    i = tasa_mensual(tasa_anual, modalidad)
    cuota = cuota_francesa(capital, tasa_anual, modalidad, meses)
    saldo = capital
    filas = []

    for n in range(1, meses + 1):
        interes = money(saldo * i)
        capital_k = money(cuota - interes)

        if n == meses:
            # Ajuste final: el redondeo acumulado deja centavos
            # sueltos. En la última cuota amortizamos el saldo
            # exacto, y la cuota final puede diferir un poco.
            capital_k = saldo
            cuota_k = money(capital_k + interes)
        else:
            cuota_k = cuota

        saldo_nuevo = money(saldo - capital_k)

        filas.append({
            "numero": n,
            "vencimiento": _sumar_meses(fecha_inicio, n),
            "capital_inicial": money(saldo),
            "interes": interes,
            "capital": capital_k,
            "cuota": cuota_k,
            "saldo": saldo_nuevo,
        })
        saldo = saldo_nuevo

    if saldo != Decimal("0.00"):
        raise ErrorInvariante(
            f"El saldo final no es cero: {saldo}. "
            "Esto indica un bug en el cálculo de la tabla."
        )
    return filas


def _tabla_alemana(
    capital: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    meses: int,
    fecha_inicio: date,
) -> list[dict]:
    """
    Tabla del sistema alemán. La amortización de capital es constante
    (capital / meses) y el interés va bajando porque se calcula sobre
    un saldo cada vez menor. Por eso la cuota decrece.
    """
    i = tasa_mensual(tasa_anual, modalidad)
    amort = money(capital / Decimal(meses))
    saldo = capital
    filas = []

    for n in range(1, meses + 1):
        interes = money(saldo * i)
        capital_k = amort
        if n == meses:
            capital_k = saldo
        cuota_k = money(capital_k + interes)
        saldo_nuevo = money(saldo - capital_k)

        filas.append({
            "numero": n,
            "vencimiento": _sumar_meses(fecha_inicio, n),
            "capital_inicial": money(saldo),
            "interes": interes,
            "capital": capital_k,
            "cuota": cuota_k,
            "saldo": saldo_nuevo,
        })
        saldo = saldo_nuevo

    if saldo != Decimal("0.00"):
        raise ErrorInvariante(f"El saldo final no es cero: {saldo}")
    return filas


def _tabla_interes_only(
    capital: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    meses: int,
    fecha_inicio: date,
    meses_interes_only: int,
) -> list[dict]:
    """
    Tabla con período de gracia. Durante los primeros N meses solo
    se paga interés y el capital no baja. Después, se amortiza el
    capital en el tiempo restante.
    """
    if meses_interes_only >= meses:
        raise ErrorValidacion(
            "El período de solo interés debe ser menor al plazo total"
        )

    i = tasa_mensual(tasa_anual, modalidad)
    saldo = capital
    filas = []
    meses_amort = meses - meses_interes_only
    amort_constante = (
        money(capital / Decimal(meses_amort)) if meses_amort else Decimal("0")
    )

    for n in range(1, meses + 1):
        interes = money(saldo * i)
        if n <= meses_interes_only:
            capital_k = Decimal("0.00")
        elif n == meses:
            capital_k = saldo
        else:
            capital_k = amort_constante
        cuota_k = money(capital_k + interes)
        saldo_nuevo = money(saldo - capital_k)

        filas.append({
            "numero": n,
            "vencimiento": _sumar_meses(fecha_inicio, n),
            "capital_inicial": money(saldo),
            "interes": interes,
            "capital": capital_k,
            "cuota": cuota_k,
            "saldo": saldo_nuevo,
        })
        saldo = saldo_nuevo

    if saldo != Decimal("0.00"):
        raise ErrorInvariante(f"El saldo final no es cero: {saldo}")
    return filas