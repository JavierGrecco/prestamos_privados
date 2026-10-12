"""
Cálculo de intereses con diferentes convenciones de conteo de días.

Este módulo responde a una pregunta: dado un saldo y una tasa anual,
¿cuánto interés se devenga entre dos fechas?

La respuesta depende de tres cosas:
  1. Cómo se convierte la tasa anual en una tasa del período
     (TNA/12 o TEA^(1/12) - 1).
  2. Cuántos días pasaron entre las dos fechas.
  3. Qué convención se usa para dividir esos días por el año.

Cada préstamo declara su convención al crearse, y a partir de ahí
todos los cálculos son consistentes.
"""
from datetime import date
from decimal import Decimal

from .tipos import ModalidadTasa, ConvencionDias, rate, money
from .excepciones import ErrorValidacion
from .convenciones_fechas import fraccion_anual_por_fechas, tasa_periodo_por_fechas


def es_bisiesto(anio: int) -> bool:
    """
    Devuelve True si el año es bisiesto.

    Un año es bisiesto si es divisible por 4, excepto los siglos
    que no son divisibles por 400. Por eso 2000 fue bisiesto pero
    1900 no.
    """
    return anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)


def tasa_mensual(tasa_anual: Decimal, modalidad: ModalidadTasa) -> Decimal:
    """
    Convierte la tasa anual a tasa mensual según la modalidad.

    TNA: la conversión es lineal. TEM = TNA / 12.
    TEA: la conversión es compuesta. TEM = (1 + TEA)^(1/12) - 1.

    Ejemplo:
        >>> tasa_mensual(Decimal("0.30"), ModalidadTasa.TNA)
        Decimal('0.02500000')

        >>> tasa_mensual(Decimal("0.30"), ModalidadTasa.TEA)
        Decimal('0.02210445')  # Aproximadamente 2.21%
    """
    if modalidad == ModalidadTasa.TNA:
        return rate(tasa_anual / Decimal("12"))
    elif modalidad == ModalidadTasa.TEA:
        # Python no tiene raíz 12 nativa para Decimal, así que
        # pasamos por float y volvemos a Decimal. La pérdida de
        # precisión es despreciable para tasas razonables.
        tem = (1 + float(tasa_anual)) ** (1 / 12) - 1
        return rate(tem)
    raise ErrorValidacion(f"Modalidad de tasa desconocida: {modalidad}")


def interes_periodo(
    saldo: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    convencion: ConvencionDias,
    fecha_ini: date,
    fecha_fin: date,
) -> Decimal:
    """Calcula el interés entre dos fechas con la convención y modalidad declaradas.

    La ruta MENSUAL conserva el contrato legado: aplica una tasa mensual
    completa a cada período positivo, sin prorratear por días reales. Las
    demás convenciones usan la misma fracción anual y conversión TNA/TEA que
    la amortización por calendario explícito.
    """
    if not isinstance(saldo, Decimal) or not saldo.is_finite():
        raise ErrorValidacion("El saldo debe ser un Decimal finito")
    if not isinstance(tasa_anual, Decimal) or not tasa_anual.is_finite():
        raise ErrorValidacion("La tasa anual debe ser un Decimal finito")
    if saldo < 0:
        raise ErrorValidacion(
            "Un saldo negativo no puede devengar interés. "
            "Revisá si estás calculando mal el saldo."
        )
    if tasa_anual < 0:
        raise ErrorValidacion("La tasa anual no puede ser negativa")
    if not isinstance(fecha_ini, date) or not isinstance(fecha_fin, date):
        raise ErrorValidacion("Las fechas del período deben ser fechas válidas")
    if fecha_fin <= fecha_ini:
        return Decimal("0.00")

    if convencion == ConvencionDias.MENSUAL:
        # Compatibilidad deliberada: un período mensual positivo utiliza una TEM.
        return money(saldo * tasa_mensual(tasa_anual, modalidad))

    fraccion = fraccion_anual_por_fechas(
        fecha_ini,
        fecha_fin,
        convencion,
    )
    factor_periodo = tasa_periodo_por_fechas(
        tasa_anual=tasa_anual,
        modalidad=modalidad,
        fraccion_anual=fraccion,
    )
    return money(saldo * factor_periodo)
