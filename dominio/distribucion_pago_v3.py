"""Distribución determinista de cobros entre inversores."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Sequence

from .excepciones import ErrorInvariante, ErrorValidacion
from .tipos import ZERO, money, rate

CENT = Decimal("0.01")


@dataclass(frozen=True)
class ParticipacionPagoV3:
    inversor_id: int
    porcentaje: Decimal

    def __post_init__(self) -> None:
        if self.inversor_id <= 0:
            raise ErrorValidacion("El inversor debe tener un ID positivo")
        p = rate(self.porcentaje)
        if p < ZERO or p > Decimal("1"):
            raise ErrorValidacion("El porcentaje de participación debe estar entre 0 y 1")
        object.__setattr__(self, "porcentaje", p)


@dataclass(frozen=True)
class AsignacionInversorPagoV3:
    inversor_id: int
    monto: Decimal

    def __post_init__(self) -> None:
        if self.inversor_id <= 0:
            raise ErrorValidacion("El inversor debe tener un ID positivo")
        m = money(self.monto)
        if m < ZERO:
            raise ErrorValidacion("El monto distribuido no puede ser negativo")
        object.__setattr__(self, "monto", m)


def distribuir_pago_v3(
    monto: Decimal,
    participaciones: Sequence[ParticipacionPagoV3],
) -> tuple[AsignacionInversorPagoV3, ...]:
    """Distribuye un monto con método de mayores residuos a centavos."""
    monto = money(monto)
    if monto <= ZERO:
        raise ErrorValidacion("El monto a distribuir debe ser mayor a cero")
    partes = tuple(participaciones)
    if not partes:
        raise ErrorValidacion("No hay participaciones para distribuir")
    ids = [p.inversor_id for p in partes]
    if len(ids) != len(set(ids)):
        raise ErrorInvariante("Un mismo inversor aparece más de una vez en las participaciones")

    suma = rate(sum((p.porcentaje for p in partes), ZERO))
    if suma != rate(Decimal("1")):
        raise ErrorInvariante(
            f"Las participaciones activas deben sumar 100%; suma={suma}"
        )

    calculos: list[tuple[int, Decimal, Decimal]] = []
    asignado = ZERO
    for p in partes:
        bruto = monto * p.porcentaje
        base = bruto.quantize(CENT, rounding=ROUND_DOWN)
        resto = bruto - base
        calculos.append((p.inversor_id, base, resto))
        asignado += base

    restante = money(monto - asignado)
    if restante < ZERO or restante % CENT != ZERO:
        raise ErrorInvariante("El redondeo de distribución produjo un remanente inválido")

    centavos = int(restante / CENT)
    orden = sorted(calculos, key=lambda x: (-x[2], x[0]))
    adicionales = {inversor_id: 0 for inversor_id, _, _ in calculos}
    for i in range(centavos):
        adicionales[orden[i % len(orden)][0]] += 1

    resultado = tuple(
        AsignacionInversorPagoV3(
            inversor_id=inversor_id,
            monto=money(base + CENT * adicionales[inversor_id]),
        )
        for inversor_id, base, _ in calculos
    )
    if money(sum((a.monto for a in resultado), ZERO)) != monto:
        raise ErrorInvariante("La distribución no conserva el monto total")
    return resultado
