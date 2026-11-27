"""
Tipos base del dominio financiero.

Este módulo define las reglas fundamentales sobre cómo se representa
el dinero, las tasas y los enums que usan todos los demás módulos.

La regla más importante de todo el sistema está acá:

    El dinero NUNCA se representa con float.

Se usa Decimal, que permite aritmética decimal exacta. Un float como
0.1 + 0.2 da 0.30000000000000004, y eso en finanzas es inaceptable.
Decimal("0.1") + Decimal("0.2") da exactamente Decimal("0.3").

Otra decisión importante: las tasas se guardan con 8 decimales de
precisión. Esto es porque TEA a TEM requiere raíces de 12, y con menos
decimales se acumulan errores al calcular intereses sobre saldos grandes.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext
from enum import Enum

from .excepciones import ErrorValidacion

# Alta precisión para cálculos intermedios. El redondeo se aplica
# solo en las fronteras (persistencia y presentación al usuario).
# 28 dígitos es el estándar de Python y sobra para cualquier cálculo.
getcontext().prec = 28

# Cuántos decimales tiene un centavo. Todo monto monetario final
# se redondea a este valor.
CENT = Decimal("0.01")

# Cuántos decimales de precisión tienen las tasas.
PRECISION_TASA = Decimal("0.00000001")
ZERO = Decimal("0")


def _decimal_finito(valor: object, etiqueta: str) -> Decimal:
    """Convierte una entrada a Decimal y rechaza valores no finitos."""
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ErrorValidacion(
            f"{etiqueta} debe ser un valor decimal válido"
        ) from exc

    if not numero.is_finite():
        raise ErrorValidacion(f"{etiqueta} debe ser un Decimal finito")

    return numero


def money(valor) -> Decimal:
    """
    Convierte un importe a Decimal con 2 decimales y ROUND_HALF_UP.

    Rechaza NaN e infinitos antes de cuantizar. El redondeo se mantiene
    deliberadamente en esta función; las fronteras de aplicación que
    requieren centavos exactos deben seguir validando sin redondear.
    """
    numero = _decimal_finito(valor, "El importe monetario")
    try:
        return numero.quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ErrorValidacion(
            "El importe monetario está fuera del rango admitido"
        ) from exc


def rate(valor) -> Decimal:
    """
    Convierte una tasa o coeficiente a Decimal con 8 decimales.

    Rechaza NaN e infinitos antes de cuantizar. No valida el rango
    contractual de la tasa: esa responsabilidad pertenece a la regla
    de dominio que conoce el producto y la operación.
    """
    numero = _decimal_finito(valor, "La tasa o coeficiente")
    try:
        return numero.quantize(PRECISION_TASA, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ErrorValidacion(
            "La tasa o coeficiente está fuera del rango admitido"
        ) from exc


class SistemaAmortizacion(str, Enum):
    """
    Sistemas de amortización soportados.

    FRANCES: cuota fija, el interés baja y la amortización sube.
             Es el más común en préstamos personales.
    ALEMAN:  amortización constante, la cuota baja con el tiempo.
             Se usa cuando se quiere devolver capital rápido.
    INTERES_ONLY: período de gracia donde solo se paga interés,
                  y después se amortiza el capital.
    PERSONALIZADO: el usuario define las cuotas a mano.
    """
    FRANCES = "frances"
    ALEMAN = "aleman"
    INTERES_ONLY = "interes_only"
    PERSONALIZADO = "personalizado"


class ModalidadTasa(str, Enum):
    """
    Modalidad de la tasa anual.

    TNA (Tasa Nominal Anual): se divide por 12 para obtener la mensual.
        Es una simplificación. Ejemplo: TNA 30% → TEM 2.5%.
    TEA (Tasa Efectiva Anual): se aplica raíz 12 para obtener la mensual.
        Es la tasa real compuesta. Ejemplo: TEA 30% → TEM 2.21%.

    La diferencia importa: TNA 30% equivale a TEA 34.49%.
    """
    TNA = "TNA"
    TEA = "TEA"


class ConvencionDias(str, Enum):
    """
    Convenciones para contar días en los cálculos de intereses.

    MENSUAL: se asume que cada mes tiene exactamente 1/12 del año.
             Simple, previsible, común en préstamos personales.
    ACTUAL_365: se cuentan los días reales y se divide por 365.
                Estándar en bonos y préstamos internacionales.
    ACTUAL_360: igual pero divide por 360. Común en EE.UU.
    TREINTA_360: valor histórico persistido como "30_360". La implementación
                 por fechas usa la regla 30E/360 ISDA; no es intercambiable
                 con cualquier variante contractual 30/360.
    ACTUAL_ACTUAL: divide los días de cada tramo de año natural por 365/366
                   (regla tipo Actual/Actual ISDA); no representa todas las
                   variantes de Actual/Actual del mercado.
    """
    MENSUAL = "mensual"
    ACTUAL_365 = "actual_365"
    ACTUAL_360 = "actual_360"
    TREINTA_360 = "30_360"
    ACTUAL_ACTUAL = "actual_actual"


class ConceptoImputacion(str, Enum):
    """
    Conceptos a los que se puede aplicar un pago.

    El orden en que se aplican importa y es configurable. Por defecto
    se cubren primero los conceptos más urgentes (mora, gastos) y
    después el capital.
    """
    GASTO = "GASTO"
    PENALIZACION = "PENALIZACION"
    MORA = "MORA"
    INTERES = "INTERES"
    CAPITAL = "CAPITAL"


# Orden por defecto de imputación. Se puede cambiar por préstamo.
# La lógica es: primero lo urgente (gastos, mora), después lo
# devengado (interés) y por último el capital.


class TipoRecalculo(str, Enum):
    RAI = "RAI"
    RNI = "RNI"

ORDEN_DEFAULT_IMPUTACION = [
    ConceptoImputacion.GASTO,
    ConceptoImputacion.PENALIZACION,
    ConceptoImputacion.MORA,
    ConceptoImputacion.INTERES,
    ConceptoImputacion.CAPITAL,
]
