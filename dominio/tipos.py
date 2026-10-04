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
from decimal import Decimal, ROUND_HALF_UP, getcontext
from enum import Enum

# Alta precisión para cálculos intermedios. El redondeo se aplica
# solo en las fronteras (persistencia y presentación al usuario).
# 28 dígitos es el estándar de Python y sobra para cualquier cálculo.
getcontext().prec = 28

# Cuántos decimales tiene un centavo. Todo monto monetario final
# se redondea a este valor.
CENT = Decimal("0.01")

# Cuántos decimales de precisión tienen las tasas.
PRECISION_TASA = Decimal("0.00000001")


def money(valor) -> Decimal:
    """
    Convierte cualquier valor a Decimal con 2 decimales, usando
    redondeo bancario-comercial (ROUND_HALF_UP).

    ¿Por qué ROUND_HALF_UP y no otro?
    Porque es el que usa la mayoría de los sistemas contables. Cuando
    un valor cae exactamente en la mitad (ej: 0.005), redondea hacia
    arriba. Otros modos (como ROUND_HALF_EVEN) son válidos para
    estadística, pero no para contabilidad.

    Ejemplo:
        >>> money("100.555")
        Decimal('100.56')
        >>> money(100)
        Decimal('100.00')
    """
    return Decimal(str(valor)).quantize(CENT, rounding=ROUND_HALF_UP)


def rate(valor) -> Decimal:
    """
    Convierte cualquier valor a Decimal con 8 decimales de precisión.
    Se usa para tasas de interés, porcentajes y coeficientes.

    Ejemplo:
        >>> rate("0.025")
        Decimal('0.02500000')
        >>> rate(0.3)
        Decimal('0.30000000')
    """
    return Decimal(str(valor)).quantize(PRECISION_TASA, rounding=ROUND_HALF_UP)


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
    Convenciones para contar días en el cálculo de intereses.

    MENSUAL: se asume que cada mes tiene exactamente 1/12 del año.
             Simple, previsible, común en préstamos personales.
    ACTUAL_365: se cuentan los días reales y se divide por 365.
                Estándar en bonos y préstamos internacionales.
    ACTUAL_360: igual pero divide por 360. Común en EE.UU.
    TREINTA_360: cada mes tiene 30 días. Simplifica cálculos.
    ACTUAL_ACTUAL: cuenta días reales y ajusta por año bisiesto.
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
ORDEN_DEFAULT_IMPUTACION = [
    ConceptoImputacion.GASTO,
    ConceptoImputacion.PENALIZACION,
    ConceptoImputacion.MORA,
    ConceptoImputacion.INTERES,
    ConceptoImputacion.CAPITAL,
]