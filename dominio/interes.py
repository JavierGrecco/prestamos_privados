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
    """
    Calcula el interés devengado entre dos fechas.

    Parámetros:
        saldo: capital sobre el que se calcula el interés.
        tasa_anual: tasa nominal o efectiva anual (0.30 = 30%).
        modalidad: TNA o TEA.
        convencion: cómo contar los días del período.
        fecha_ini: fecha desde la que se devenga.
        fecha_fin: fecha hasta la que se devenga.

    Devuelve el interés como Decimal redondeado a 2 decimales.

    Ejemplo:
        >>> interes_periodo(
        ...     saldo=Decimal("1000000"),
        ...     tasa_anual=Decimal("0.36"),
        ...     modalidad=ModalidadTasa.TNA,
        ...     convencion=ConvencionDias.ACTUAL_365,
        ...     fecha_ini=date(2026, 1, 1),
        ...     fecha_fin=date(2026, 1, 31),
        ... )
        Decimal('29589.04')
    """
    if saldo < 0:
        raise ErrorValidacion(
            "Un saldo negativo no puede devengar interés. "
            "Revisá si estás calculando mal el saldo."
        )

    if convencion == ConvencionDias.MENSUAL:
        # La convención mensual ignora los días reales: aplica
        # siempre la tasa mensual completa, sin importar si el
        # mes tiene 28, 30 o 31 días.
        i = tasa_mensual(tasa_anual, modalidad)
        return money(saldo * i)

    dias = Decimal((fecha_fin - fecha_ini).days)
    if dias <= 0:
        return Decimal("0.00")

    if convencion == ConvencionDias.ACTUAL_365:
        return money(saldo * tasa_anual * dias / Decimal("365"))

    if convencion == ConvencionDias.ACTUAL_360:
        return money(saldo * tasa_anual * dias / Decimal("360"))

    if convencion == ConvencionDias.TREINTA_360:
        # En esta convención cada mes tiene exactamente 30 días.
        # Por eso siempre se divide por 30/360, sin importar
        # cuántos días reales pasaron.
        return money(saldo * tasa_anual * Decimal("30") / Decimal("360"))

    if convencion == ConvencionDias.ACTUAL_ACTUAL:
        # La diferencia con ACTUAL_365 es que en año bisiesto se
        # divide por 366 en lugar de 365.
        dias_anio = Decimal("366") if es_bisiesto(fecha_ini.year) else Decimal("365")
        return money(saldo * tasa_anual * dias / dias_anio)

    raise ErrorValidacion(f"Convención de días desconocida: {convencion}")