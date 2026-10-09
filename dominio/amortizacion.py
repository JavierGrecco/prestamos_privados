"""
Generación de tablas de amortización.

Este es el corazón del motor financiero. Dado un capital, una tasa,
un plazo y un sistema, genera la lista de cuotas con su desglose.

La regla fundamental: la última cuota se ajusta para que el saldo
final sea EXACTAMENTE cero. Esto es necesario porque el redondeo a
centavos deja pequeñas diferencias que se acumulan. En lugar de
arrastrar centavos, se ajusta la última cuota y se registra el ajuste.
"""
from calendar import isleap, monthrange
from datetime import date
from decimal import Decimal, localcontext

from dateutil.relativedelta import relativedelta

from .tipos import SistemaAmortizacion, ModalidadTasa, ConvencionDias, money, rate
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


def fraccion_anual_por_fechas(
    fecha_inicio: date,
    fecha_fin: date,
    convencion: ConvencionDias,
    *,
    fecha_fin_es_vencimiento_final: bool = False,
) -> Decimal:
    """Devuelve la fracción anual entre fechas para una convención explícita.

    TREINTA_360 se interpreta como 30E/360 Eurobond. Se normalizan los fines
    de mes al día 30, salvo el vencimiento final que cae en febrero, que
    conserva su día real. MENSUAL se gestiona por la ruta compatible
    de generar_tabla y no usa fracciones de días.
    """
    if fecha_fin <= fecha_inicio:
        raise ErrorValidacion("Cada vencimiento debe ser posterior al inicio del período")

    dias_reales = (fecha_fin - fecha_inicio).days
    if convencion == ConvencionDias.ACTUAL_365:
        return Decimal(dias_reales) / Decimal("365")
    if convencion == ConvencionDias.ACTUAL_360:
        return Decimal(dias_reales) / Decimal("360")
    if convencion == ConvencionDias.ACTUAL_ACTUAL:
        cursor = fecha_inicio
        fraccion = Decimal("0")
        while cursor < fecha_fin:
            inicio_siguiente_anio = date(cursor.year + 1, 1, 1)
            fin_tramo = min(fecha_fin, inicio_siguiente_anio)
            base = Decimal("366") if isleap(cursor.year) else Decimal("365")
            fraccion += Decimal((fin_tramo - cursor).days) / base
            cursor = fin_tramo
        return fraccion
    if convencion == ConvencionDias.TREINTA_360:
        ultimo_inicio = monthrange(fecha_inicio.year, fecha_inicio.month)[1]
        ultimo_fin = monthrange(fecha_fin.year, fecha_fin.month)[1]
        dia_inicio = 30 if fecha_inicio.day == ultimo_inicio else min(fecha_inicio.day, 30)
        fin_es_febrero = fecha_fin.month == 2 and fecha_fin.day == ultimo_fin
        conservar_fin_febrero = fecha_fin_es_vencimiento_final and fin_es_febrero
        dia_fin = (
            fecha_fin.day
            if conservar_fin_febrero
            else 30 if fecha_fin.day == ultimo_fin else min(fecha_fin.day, 30)
        )
        dias_30_360 = (
            (fecha_fin.year - fecha_inicio.year) * 360
            + (fecha_fin.month - fecha_inicio.month) * 30
            + dia_fin
            - dia_inicio
        )
        return Decimal(dias_30_360) / Decimal("360")
    if convencion == ConvencionDias.MENSUAL:
        raise ErrorValidacion(
            "La convención mensual requiere vencimientos en aniversarios mensuales"
        )
    raise ErrorValidacion(f"Convención de días no soportada: {convencion}")


def tasa_periodo_por_fechas(
    *,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    fraccion_anual: Decimal,
) -> Decimal:
    """Convierte la tasa anual a tasa de período sin usar aritmética float.

    TNA usa una tasa proporcional a la fracción anual. TEA aplica un factor
    compuesto: (1 + TEA) elevado a la fracción del año, menos uno.
    """
    if tasa_anual < 0:
        raise ErrorValidacion("La tasa anual no puede ser negativa")
    if fraccion_anual <= 0:
        raise ErrorValidacion("La fracción anual del período debe ser positiva")
    if modalidad == ModalidadTasa.TNA:
        return rate(tasa_anual * fraccion_anual)
    if modalidad == ModalidadTasa.TEA:
        with localcontext() as contexto:
            contexto.prec = 40
            factor = contexto.power(
                Decimal("1") + tasa_anual, fraccion_anual
            ) - Decimal("1")
            return rate(factor)
    raise ErrorValidacion(f"Modalidad de tasa desconocida: {modalidad}")


def generar_tabla_por_fechas(
    *,
    capital: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    sistema: SistemaAmortizacion,
    fecha_inicio_periodo: date,
    fechas_vencimiento: list[date] | tuple[date, ...],
    convencion: ConvencionDias,
) -> list[dict]:
    """Genera una tabla de amortización para un calendario explícito.

    fecha_inicio_periodo es la fecha desde la que devenga el primer período
    regular, no necesariamente el desembolso del préstamo. La carencia inicial
    debe calcularse y tratarse por separado.

    Con convención MENSUAL exige aniversarios mensuales anclados a la fecha
    inicial y delega al motor legado, para preservar sus resultados exactos.
    Con convenciones por días, calcula el factor de cada período desde las
    dos fechas explícitas.

    Admite FRANCES y ALEMAN. INTERES_ONLY conserva su ruta especializada y no
    se combina implícitamente con calendarios irregulares.
    """
    if capital <= 0:
        raise ErrorValidacion("El capital debe ser mayor a cero")
    if tasa_anual < 0:
        raise ErrorValidacion("La tasa anual no puede ser negativa")
    if not isinstance(fecha_inicio_periodo, date):
        raise ErrorValidacion("La fecha de inicio del período debe ser una fecha")
    if not fechas_vencimiento:
        raise ErrorValidacion("Debe existir al menos una fecha de vencimiento")
    if sistema not in {SistemaAmortizacion.FRANCES, SistemaAmortizacion.ALEMAN}:
        raise ErrorValidacion(
            "El calendario explícito solo admite sistemas FRANCES y ALEMAN; "
            "INTERES_ONLY requiere su ruta especializada"
        )
    if any(not isinstance(fecha, date) for fecha in fechas_vencimiento):
        raise ErrorValidacion("Todas las fechas de vencimiento deben ser fechas")
    if any(fecha <= fecha_inicio_periodo for fecha in fechas_vencimiento):
        raise ErrorValidacion(
            "Todos los vencimientos deben ser posteriores al inicio del período"
        )
    if any(
        posterior <= anterior
        for anterior, posterior in zip(fechas_vencimiento, fechas_vencimiento[1:])
    ):
        raise ErrorValidacion("Las fechas de vencimiento deben estar estrictamente ordenadas")

    meses = len(fechas_vencimiento)
    if convencion == ConvencionDias.MENSUAL:
        calendario_esperado = tuple(
            _sumar_meses(fecha_inicio_periodo, numero)
            for numero in range(1, meses + 1)
        )
        if tuple(fechas_vencimiento) != calendario_esperado:
            raise ErrorValidacion(
                "Con convención MENSUAL, los vencimientos deben respetar los "
                "aniversarios mensuales calculados desde la fecha de inicio. "
                "Elegí una convención de días reales o 30E/360 para un primer "
                "período irregular."
            )
        return generar_tabla(
            capital=capital,
            tasa_anual=tasa_anual,
            modalidad=modalidad,
            meses=meses,
            fecha_inicio=fecha_inicio_periodo,
            sistema=sistema,
        )

    tasas_periodo: list[Decimal] = []
    fecha_anterior = fecha_inicio_periodo
    for vencimiento in fechas_vencimiento:
        fraccion = fraccion_anual_por_fechas(
            fecha_anterior,
            vencimiento,
            convencion,
            fecha_fin_es_vencimiento_final=(vencimiento == fechas_vencimiento[-1]),
        )
        tasas_periodo.append(
            tasa_periodo_por_fechas(
                tasa_anual=tasa_anual,
                modalidad=modalidad,
                fraccion_anual=fraccion,
            )
        )
        fecha_anterior = vencimiento

    if sistema == SistemaAmortizacion.FRANCES:
        with localcontext() as contexto:
            contexto.prec = 40
            acumulado = Decimal("1")
            factor_presente = Decimal("0")
            for tasa_periodo in tasas_periodo:
                acumulado *= Decimal("1") + tasa_periodo
                factor_presente += Decimal("1") / acumulado
            cuota_teorica = money(capital / factor_presente)
    else:
        cuota_teorica = Decimal("0.00")

    saldo = money(capital)
    amortizacion_alemana = money(capital / Decimal(meses))
    filas: list[dict] = []
    for indice, (vencimiento, tasa_periodo) in enumerate(
        zip(fechas_vencimiento, tasas_periodo), start=1
    ):
        interes = money(saldo * tasa_periodo)
        if sistema == SistemaAmortizacion.FRANCES:
            capital_periodo = money(cuota_teorica - interes)
            if indice < meses and capital_periodo < Decimal("0.00"):
                raise ErrorValidacion(
                    "La cuota francesa fija no cubre el interés de uno de los "
                    "períodos; revisá las fechas y la convención elegida"
                )
            if indice == meses:
                capital_periodo = saldo
                cuota = money(capital_periodo + interes)
            else:
                cuota = cuota_teorica
        else:
            capital_periodo = saldo if indice == meses else amortizacion_alemana
            cuota = money(capital_periodo + interes)

        saldo_nuevo = money(saldo - capital_periodo)
        if saldo_nuevo < Decimal("0.00"):
            raise ErrorInvariante(
                f"El saldo del período {indice} no puede ser negativo: {saldo_nuevo}"
            )
        filas.append({
            "numero": indice,
            "vencimiento": vencimiento,
            "capital_inicial": money(saldo),
            "interes": interes,
            "capital": capital_periodo,
            "cuota": cuota,
            "saldo": saldo_nuevo,
        })
        saldo = saldo_nuevo

    if saldo != Decimal("0.00"):
        raise ErrorInvariante(f"El saldo final no es cero: {saldo}")
    if sum((fila["capital"] for fila in filas), start=Decimal("0.00")) != money(capital):
        raise ErrorInvariante("La suma de amortizaciones no coincide con el capital")
    return filas
