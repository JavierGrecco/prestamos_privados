"""Convenciones temporales compartidas por intereses y amortización.

Este módulo es la autoridad común para transformar fechas en una fracción
anual y convertir TNA/TEA a un factor de período. No conoce préstamos ni
persistencia y no depende del generador de cuotas.
"""
from calendar import isleap, monthrange
from datetime import date
from decimal import Decimal, localcontext

from .excepciones import ErrorValidacion
from .tipos import ConvencionDias, ModalidadTasa, rate


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
    if not tasa_anual.is_finite():
        raise ErrorValidacion("La tasa anual debe ser un Decimal finito")
    if tasa_anual < 0:
        raise ErrorValidacion("La tasa anual no puede ser negativa")
    if not fraccion_anual.is_finite() or fraccion_anual <= 0:
        raise ErrorValidacion("La fracción anual del período debe ser finita y positiva")
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
