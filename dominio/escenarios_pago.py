"""
Reglas puras para analizar un pago antes de registrarlo.

Este módulo no conoce préstamos, SQLite ni Streamlit. Recibe el estado
financiero de una deuda y devuelve qué parte del pago cubre cada concepto
junto con el efecto que tendría sobre el período siguiente.
"""
from dataclasses import dataclass
from decimal import Decimal

from .politica_pago import ORDEN_WATERFALL_CANONICO, PoliticaImputacionPago
from .tipos import ConceptoImputacion, money
from .excepciones import ErrorValidacion


@dataclass(frozen=True)
class DeudaPago:
    """Deuda disponible para imputar en un momento concreto."""

    cuota_interes: Decimal = Decimal("0.00")
    cuota_capital: Decimal = Decimal("0.00")
    arrastre_interes: Decimal = Decimal("0.00")
    arrastre_capital: Decimal = Decimal("0.00")
    arrastre_mora: Decimal = Decimal("0.00")
    interes_extra: Decimal = Decimal("0.00")
    mora_nueva: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        # Normalizamos una sola vez para no mezclar importes con distinta
        # precisión durante el reparto del pago.
        for nombre in (
            "cuota_interes",
            "cuota_capital",
            "arrastre_interes",
            "arrastre_capital",
            "arrastre_mora",
            "interes_extra",
            "mora_nueva",
        ):
            valor = money(getattr(self, nombre))
            if valor < 0:
                raise ErrorValidacion(f"La deuda no puede tener {nombre} negativo")
            object.__setattr__(self, nombre, valor)

    @property
    def deuda_mora(self) -> Decimal:
        return money(self.arrastre_mora + self.mora_nueva)

    @property
    def deuda_interes(self) -> Decimal:
        return money(
            self.arrastre_interes + self.cuota_interes + self.interes_extra
        )

    @property
    def deuda_capital(self) -> Decimal:
        return money(self.arrastre_capital + self.cuota_capital)

    @property
    def total(self) -> Decimal:
        return money(self.deuda_mora + self.deuda_interes + self.deuda_capital)


@dataclass(frozen=True)
class ResultadoPago:
    """Resultado de una simulación de imputación, sin guardar nada."""

    monto: Decimal
    total_deuda: Decimal
    tipo: str
    aplicado_mora: Decimal
    aplicado_interes: Decimal
    aplicado_capital: Decimal
    faltante: Decimal
    excedente: Decimal
    capital_pendiente_despues: Decimal
    interes_extra_estimado_proximo_periodo: Decimal
    interes_extra_generado_por_pago: Decimal

    @property
    def cubre_deuda(self) -> bool:
        return self.faltante == Decimal("0.00")

    @property
    def es_parcial(self) -> bool:
        return self.tipo == "PARCIAL"

    @property
    def es_adelanto(self) -> bool:
        return self.tipo == "ADELANTO"


def simular_pago(
    monto: Decimal,
    deuda: DeudaPago,
    tasa_mensual: Decimal | None = None,
    *,
    orden_imputacion: tuple[ConceptoImputacion, ...] = ORDEN_WATERFALL_CANONICO,
    politica: PoliticaImputacionPago | None = None,
) -> ResultadoPago:
    """
    Simula cómo se aplicaría un pago siguiendo las reglas actuales.

    El orden es mora → interés → capital. Un pago menor deja un faltante;
    uno mayor que la deuda genera un excedente que luego puede tratarse
    como adelanto de capital.

    Se informan dos efectos distintos sobre el período siguiente:

    - ``interes_extra_generado_por_pago``: interés atribuible al capital de
      la cuota actual que queda impago después de este pago.
    - ``interes_extra_estimado_proximo_periodo``: interés total que se
      proyecta para el próximo período sobre todo el capital que seguirá
      pendiente, incluyendo arrastres anteriores.

    Mantener ambos conceptos evita confundir el costo causado por esta
    decisión con el costo total que tendrá la deuda el mes siguiente.
    """
    monto = money(monto)
    if monto <= 0:
        raise ErrorValidacion("El monto del pago debe ser mayor a cero")

    orden = tuple(politica.orden_waterfall if politica is not None else orden_imputacion)
    if not orden or len(set(orden)) != len(orden):
        raise ErrorValidacion("El orden de imputacion no puede estar vacio ni repetir conceptos")
    if any(not isinstance(c, ConceptoImputacion) for c in orden):
        raise ErrorValidacion("El orden de imputacion contiene conceptos invalidos")

    saldos = {
        ConceptoImputacion.MORA: deuda.deuda_mora,
        ConceptoImputacion.INTERES: deuda.deuda_interes,
        ConceptoImputacion.CAPITAL: deuda.deuda_capital,
    }
    aplicados = {
        ConceptoImputacion.MORA: Decimal("0.00"),
        ConceptoImputacion.INTERES: Decimal("0.00"),
        ConceptoImputacion.CAPITAL: Decimal("0.00"),
    }

    total = deuda.total
    resto = monto
    for concepto in orden:
        disponible = saldos.get(concepto, Decimal("0.00"))
        aplicado = min(resto, disponible)
        aplicados[concepto] = money(aplicados[concepto] + aplicado)
        resto = money(resto - aplicado)

    aplicado_mora = aplicados[ConceptoImputacion.MORA]
    aplicado_interes = aplicados[ConceptoImputacion.INTERES]
    aplicado_capital = aplicados[ConceptoImputacion.CAPITAL]

    excedente = money(resto)
    cubierto = money(aplicado_mora + aplicado_interes + aplicado_capital)
    faltante = money(total - cubierto)

    if excedente > 0:
        tipo = "ADELANTO"
    elif faltante > 0:
        tipo = "PARCIAL"
    else:
        tipo = "CUOTA"

    # La imputación real prioriza primero capital arrastrado y después
    # capital de la cuota corriente. Así podemos saber qué parte del interés
    # futuro es propia de este pago y cuál ya existía antes.
    capital_aplicado_arrastre = min(aplicado_capital, deuda.arrastre_capital)
    capital_aplicado_objetivo = money(
        aplicado_capital - capital_aplicado_arrastre
    )

    capital_arrastre_despues = money(
        deuda.arrastre_capital - capital_aplicado_arrastre
    )
    capital_objetivo_despues = money(
        deuda.cuota_capital - capital_aplicado_objetivo
    )

    capital_pendiente_despues = money(
        capital_arrastre_despues + capital_objetivo_despues
    )

    interes_extra_total = Decimal("0.00")
    interes_extra_por_pago = Decimal("0.00")
    if tasa_mensual is not None and capital_pendiente_despues > 0:
        tasa = Decimal(str(tasa_mensual))
        if tasa < 0:
            raise ErrorValidacion("La tasa mensual no puede ser negativa")
        interes_extra_total = money(capital_pendiente_despues * tasa)
        interes_extra_por_pago = money(capital_objetivo_despues * tasa)

    return ResultadoPago(
        monto=monto,
        total_deuda=total,
        tipo=tipo,
        aplicado_mora=money(aplicado_mora),
        aplicado_interes=money(aplicado_interes),
        aplicado_capital=money(aplicado_capital),
        faltante=faltante,
        excedente=excedente,
        capital_pendiente_despues=capital_pendiente_despues,
        interes_extra_estimado_proximo_periodo=interes_extra_total,
        interes_extra_generado_por_pago=interes_extra_por_pago,
    )
