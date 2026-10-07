"""Planificación pura de adelantos RAI/RNI para el Motor V3."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable, Sequence

from .excepciones import ErrorInvariante, ErrorValidacion
from .tipos import ModalidadTasa, SistemaAmortizacion, TipoRecalculo, money, ZERO


@dataclass(frozen=True)
class CuotaFuturaAdelantoV3:
    """Representación mínima e inmutable de una cuota futura vigente."""

    cuota_id: int
    numero: int
    vencimiento: date
    capital_inicial: Decimal
    interes: Decimal
    capital: Decimal
    cuota: Decimal
    saldo: Decimal

    def __post_init__(self) -> None:
        if self.cuota_id <= 0 or self.numero <= 0:
            raise ErrorValidacion("La cuota futura debe tener IDs positivos")
        if self.capital_inicial < ZERO or self.interes < ZERO or self.capital < ZERO or self.cuota < ZERO or self.saldo < ZERO:
            raise ErrorValidacion("Los importes de una cuota futura no pueden ser negativos")
        object.__setattr__(self, "capital_inicial", money(self.capital_inicial))
        object.__setattr__(self, "interes", money(self.interes))
        object.__setattr__(self, "capital", money(self.capital))
        object.__setattr__(self, "cuota", money(self.cuota))
        object.__setattr__(self, "saldo", money(self.saldo))


@dataclass(frozen=True)
class CuotaNuevaAdelantoV3:
    numero: int
    vencimiento: date
    capital_inicial: Decimal
    interes: Decimal
    capital: Decimal
    cuota: Decimal
    saldo: Decimal

    def __post_init__(self) -> None:
        if self.numero <= 0:
            raise ErrorValidacion("El número de cuota nueva debe ser positivo")
        for nombre in ("capital_inicial", "interes", "capital", "cuota", "saldo"):
            valor = money(getattr(self, nombre))
            if valor < ZERO:
                raise ErrorValidacion(f"{nombre} no puede ser negativo")
            object.__setattr__(self, nombre, valor)


@dataclass(frozen=True)
class PlanAdelantoV3:
    tipo: TipoRecalculo
    cuota_objetivo_numero: int
    capital_antes: Decimal
    capital_despues: Decimal
    monto_adelanto: Decimal
    cuotas_antes: int
    cuotas_despues: int
    intereses_antes: Decimal
    intereses_despues: Decimal
    intereses_ahorrados: Decimal
    cuotas_reemplazadas: tuple[CuotaFuturaAdelantoV3, ...]
    cuotas_nuevas: tuple[CuotaNuevaAdelantoV3, ...]

    def __post_init__(self) -> None:
        for nombre in (
            "capital_antes", "capital_despues", "monto_adelanto",
            "intereses_antes", "intereses_despues",
        ):
            valor = money(getattr(self, nombre))
            if valor < ZERO:
                raise ErrorInvariante(f"{nombre} no puede ser negativo")
            object.__setattr__(self, nombre, valor)
        if self.cuota_objetivo_numero <= 0:
            raise ErrorInvariante("El recálculo debe identificar la cuota objetivo")
        if self.cuotas_antes != len(self.cuotas_reemplazadas):
            raise ErrorInvariante("La cantidad de cuotas reemplazadas no concilia")
        if self.cuotas_despues != len(self.cuotas_nuevas):
            raise ErrorInvariante("La cantidad de cuotas nuevas no concilia")
        if self.capital_despues != money(sum((c.capital for c in self.cuotas_nuevas), ZERO)):
            raise ErrorInvariante("El capital de la nueva tabla no concilia con el capital posterior")
        if self.intereses_despues != money(sum((c.interes for c in self.cuotas_nuevas), ZERO)):
            raise ErrorInvariante("Los intereses de la nueva tabla no concilian")
        ahorro_esperado = money(self.intereses_antes - self.intereses_despues)
        if ahorro_esperado < ZERO:
            raise ErrorInvariante("Un adelanto no puede aumentar el interés total futuro")
        if self.intereses_ahorrados != ahorro_esperado:
            raise ErrorInvariante("El ahorro de intereses no concilia")


def _alinear_fechas(tabla: Sequence[dict], fechas: Sequence[date]) -> list[dict]:
    if len(tabla) > len(fechas):
        raise ErrorInvariante("La nueva tabla contiene más cuotas que fechas disponibles")
    salida = []
    for fila, vencimiento in zip(tabla, fechas):
        copia = dict(fila)
        copia["vencimiento"] = vencimiento
        salida.append(copia)
    return salida


def planificar_adelanto_v3(
    *,
    tipo: TipoRecalculo,
    cuotas_futuras: Sequence[CuotaFuturaAdelantoV3],
    monto_adelanto: Decimal,
    tasa_anual: Decimal,
    modalidad_tasa: ModalidadTasa,
    sistema: SistemaAmortizacion = SistemaAmortizacion.FRANCES,
    cuota_objetivo_numero: int | None = None,
    recalcular_rai_fn: Callable | None = None,
    recalcular_rni_fn: Callable | None = None,
) -> PlanAdelantoV3:
    """Calcula una reestructuración sin tocar DB.

    RAI conserva las fechas y la cantidad de cuotas futuras.
    RNI conserva la cuota de referencia y utiliza las primeras fechas futuras
    necesarias, acortando el vencimiento final.
    """
    cuotas = tuple(cuotas_futuras)
    if not cuotas:
        raise ErrorValidacion("No existen cuotas futuras para aplicar el adelanto")
    monto_adelanto = money(monto_adelanto)
    if monto_adelanto <= ZERO:
        raise ErrorValidacion("El monto de adelanto debe ser mayor a cero")
    if tasa_anual < ZERO:
        raise ErrorValidacion("La tasa anual no puede ser negativa")
    if any(c.saldo != ZERO and i + 1 < len(cuotas) and c.saldo < ZERO for i, c in enumerate(cuotas)):
        raise ErrorInvariante("Existe una cuota futura con saldo inválido")

    capital_antes = money(cuotas[0].capital_inicial)
    capital_despues = money(capital_antes - monto_adelanto)
    if capital_despues < ZERO:
        raise ErrorValidacion(
            f"El adelanto {monto_adelanto} excede el capital futuro {capital_antes}"
        )

    intereses_antes = money(sum((c.interes for c in cuotas), ZERO))
    if capital_despues == ZERO:
        nueva_tabla: list[dict] = []
    else:
        if tipo is TipoRecalculo.RAI:
            if recalcular_rai_fn is None:
                from .recalculo import recalcular_rai
                recalcular_rai_fn = recalcular_rai
            tabla = recalcular_rai_fn(
                capital_pendiente=capital_despues,
                tasa_anual=tasa_anual,
                modalidad=modalidad_tasa,
                meses_restantes=len(cuotas),
                fecha_ultimo_vencimiento=cuotas[-1].vencimiento,
                sistema=sistema,
            )
            nueva_tabla = _alinear_fechas(tabla, [c.vencimiento for c in cuotas])
        elif tipo is TipoRecalculo.RNI:
            if recalcular_rni_fn is None:
                from .recalculo import recalcular_rni
                recalcular_rni_fn = recalcular_rni
            tabla, n = recalcular_rni_fn(
                capital_pendiente=capital_despues,
                tasa_anual=tasa_anual,
                modalidad=modalidad_tasa,
                cuota_objetivo=cuotas[0].cuota,
                fecha_ultimo_vencimiento=cuotas[-1].vencimiento,
                sistema=sistema,
            )
            if tabla is None or n is None:
                raise ErrorValidacion("La cuota vigente no alcanza para amortizar el capital restante en RNI")
            if n > len(cuotas):
                raise ErrorInvariante("RNI aumentaría el plazo después de un adelanto")
            nueva_tabla = _alinear_fechas(tabla, [c.vencimiento for c in cuotas[:n]])
        else:
            raise ErrorValidacion(f"Tipo de recálculo no soportado: {tipo}")

    nuevas = tuple(
        CuotaNuevaAdelantoV3(
            numero=cuota.numero,
            vencimiento=fila["vencimiento"],
            capital_inicial=fila["capital_inicial"],
            interes=fila["interes"],
            capital=fila["capital"],
            cuota=fila["cuota"],
            saldo=fila["saldo"],
        )
        for cuota, fila in zip(cuotas, nueva_tabla)
    )
    intereses_despues = money(sum((c.interes for c in nuevas), ZERO))
    objetivo = cuota_objetivo_numero if cuota_objetivo_numero is not None else cuotas[0].numero - 1
    return PlanAdelantoV3(
        tipo=tipo,
        cuota_objetivo_numero=objetivo,
        capital_antes=capital_antes,
        capital_despues=capital_despues,
        monto_adelanto=monto_adelanto,
        cuotas_antes=len(cuotas),
        cuotas_despues=len(nuevas),
        intereses_antes=intereses_antes,
        intereses_despues=intereses_despues,
        intereses_ahorrados=money(intereses_antes - intereses_despues),
        cuotas_reemplazadas=cuotas,
        cuotas_nuevas=nuevas,
    )
