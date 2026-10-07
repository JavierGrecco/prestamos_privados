"""V3-D: reconstrucción pura de la trayectoria de capital real.

Este módulo convierte reducciones de capital efectivamente ocurridas en una
serie temporal de capital real. No persiste nada y no modifica un cronograma.
Está diseñado para alimentar V3-C, que compara capital real contra capital
contractual y calcula la exposición adicional.

Semántica temporal: un evento con fecha ``D`` es efectivo desde ``D``. Los
intervalos se interpretan como [fecha_desde, fecha_hasta).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable, Protocol, Sequence

from .excepciones import ErrorInvariante, ErrorValidacion
from .exposicion_capital_v3 import (
    PuntoCapitalProgramado,
    PuntoCapitalReal,
    ResultadoExposicionCapital,
    calcular_exposicion_capital,
)
from .motor_pagos_v3 import ZERO, OrigenImputacion
from .tipos import ConceptoImputacion, money


@dataclass(frozen=True)
class EventoReduccionCapital:
    """Reducción efectiva de capital ocurrida en una fecha de valor."""

    fecha_valor: date
    monto: Decimal
    origen: OrigenImputacion = OrigenImputacion.SALDO_CONTRACTUAL
    referencia: str | None = None

    def __post_init__(self) -> None:
        monto = money(self.monto)
        if monto <= ZERO:
            raise ErrorValidacion("Una reducción de capital debe ser mayor a cero")
        object.__setattr__(self, "monto", monto)


@dataclass(frozen=True)
class ResultadoTrayectoriaCapital:
    """Serie temporal de capital real y métricas de control."""

    fecha_desde: date
    fecha_hasta: date
    capital_inicial: Decimal
    puntos: tuple[PuntoCapitalReal, ...]
    reducciones_antes_del_periodo: Decimal = ZERO
    reducciones_en_el_periodo: Decimal = ZERO

    @property
    def capital_al_inicio(self) -> Decimal:
        if not self.puntos:
            return ZERO
        return self.puntos[0].capital

    @property
    def capital_al_final(self) -> Decimal:
        if not self.puntos:
            return ZERO
        return self.puntos[-1].capital

    @property
    def reduccion_total(self) -> Decimal:
        return money(
            self.reducciones_antes_del_periodo + self.reducciones_en_el_periodo
        )

    def validar(self) -> None:
        if self.fecha_hasta < self.fecha_desde:
            raise ErrorValidacion("El período de la trayectoria es inválido")
        if self.capital_inicial < ZERO:
            raise ErrorValidacion("El capital inicial no puede ser negativo")
        if not self.puntos:
            raise ErrorInvariante("Una trayectoria no vacía debe tener punto inicial")
        if self.puntos[0].fecha != self.fecha_desde:
            raise ErrorInvariante("La trayectoria no comienza en fecha_desde")
        anterior: date | None = None
        for punto in self.puntos:
            if anterior is not None and punto.fecha <= anterior:
                raise ErrorInvariante("Los puntos de capital no están estrictamente ordenados")
            if punto.capital < ZERO:
                raise ErrorInvariante("La trayectoria contiene capital negativo")
            anterior = punto.fecha
        if self.reducciones_antes_del_periodo < ZERO:
            raise ErrorInvariante("Las reducciones previas no pueden ser negativas")
        if self.reducciones_en_el_periodo < ZERO:
            raise ErrorInvariante("Las reducciones del período no pueden ser negativas")


class PlanPagoConCapital(Protocol):
    """Interfaz mínima que necesita V3-D de un PlanPago."""

    prestamo_id: int
    fecha_valor: date
    aplicaciones: Sequence[object]


def construir_trayectoria_capital_real(
    *,
    capital_inicial: Decimal,
    fecha_inicio_contrato: date,
    fecha_desde: date,
    fecha_hasta: date,
    eventos: Iterable[EventoReduccionCapital],
) -> ResultadoTrayectoriaCapital:
    """Construye el capital real por fechas a partir de reducciones efectivas.

    Los eventos anteriores a ``fecha_desde`` se incorporan al punto inicial.
    Los eventos exactamente en ``fecha_desde`` también son efectivos en ese
    punto. Los eventos exactamente en ``fecha_hasta`` quedan fuera del
    intervalo [fecha_desde, fecha_hasta).
    """
    capital_inicial = money(capital_inicial)
    if capital_inicial < ZERO:
        raise ErrorValidacion("El capital inicial no puede ser negativo")
    if fecha_desde < fecha_inicio_contrato:
        raise ErrorValidacion("fecha_desde no puede ser anterior al inicio del contrato")
    if fecha_hasta < fecha_desde:
        raise ErrorValidacion("fecha_hasta no puede ser anterior a fecha_desde")

    eventos_ordenados = _normalizar_eventos(eventos)
    for evento in eventos_ordenados:
        if evento.fecha_valor < fecha_inicio_contrato:
            raise ErrorValidacion(
                f"El evento {evento.referencia or '<sin referencia>'} es anterior al contrato"
            )

    capital = capital_inicial
    previas = ZERO
    periodo = ZERO
    eventos_en_periodo: list[EventoReduccionCapital] = []

    for evento in eventos_ordenados:
        if evento.fecha_valor <= fecha_desde:
            capital = _reducir_capital(capital, evento)
            if evento.fecha_valor < fecha_desde:
                previas = money(previas + evento.monto)
        elif evento.fecha_valor < fecha_hasta:
            eventos_en_periodo.append(evento)

    puntos: list[PuntoCapitalReal] = [
        PuntoCapitalReal(
            fecha=fecha_desde,
            capital=capital,
            referencia="TRAYECTORIA:INICIO",
        )
    ]

    for fecha, eventos_fecha in _agrupar_por_fecha(eventos_en_periodo):
        for evento in eventos_fecha:
            capital = _reducir_capital(capital, evento)
            periodo = money(periodo + evento.monto)
        referencias = tuple(
            sorted(
                ref
                for ref in (evento.referencia for evento in eventos_fecha)
                if ref
            )
        )
        referencia = "|".join(referencias) if referencias else f"EVENTOS:{fecha.isoformat()}"
        puntos.append(PuntoCapitalReal(fecha=fecha, capital=capital, referencia=referencia))

    resultado = ResultadoTrayectoriaCapital(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        capital_inicial=capital_inicial,
        puntos=tuple(puntos),
        reducciones_antes_del_periodo=previas,
        reducciones_en_el_periodo=periodo,
    )
    resultado.validar()
    return resultado


def eventos_capital_desde_plan(
    plan: PlanPagoConCapital,
    *,
    referencia_pago: str | None = None,
) -> tuple[EventoReduccionCapital, ...]:
    """Extrae sólo aplicaciones de CAPITAL de un PlanPago.

    No requiere que el PlanPago sea de una clase concreta: utiliza la interfaz
    mínima del contrato. La capa de aplicación puede suministrar un ID real
    de pago mediante ``referencia_pago`` cuando exista.
    """
    eventos: list[EventoReduccionCapital] = []
    for aplicacion in plan.aplicaciones:
        concepto = getattr(aplicacion, "concepto", None)
        if concepto is not ConceptoImputacion.CAPITAL:
            continue
        monto = getattr(aplicacion, "monto", None)
        cuota_id = getattr(aplicacion, "cuota_id", None)
        origen = getattr(aplicacion, "origen", OrigenImputacion.SALDO_CONTRACTUAL)
        if monto is None or cuota_id is None:
            raise ErrorValidacion("La aplicación de capital no tiene monto o cuota_id")
        referencia_base = referencia_pago or f"PLAN:{plan.prestamo_id}:{plan.fecha_valor.isoformat()}"
        referencia = f"{referencia_base}:CUOTA_{cuota_id}"
        eventos.append(
            EventoReduccionCapital(
                fecha_valor=plan.fecha_valor,
                monto=monto,
                origen=origen,
                referencia=referencia,
            )
        )
    return tuple(eventos)


def calcular_exposicion_desde_eventos_capital(
    *,
    capital_inicial: Decimal,
    fecha_inicio_contrato: date,
    fecha_desde: date,
    fecha_hasta: date,
    eventos_capital: Iterable[EventoReduccionCapital],
    capital_programado: Sequence[PuntoCapitalProgramado],
    politica_interes,
    referencia_resultado: str = "EXPOSICION_CAPITAL_V3D",
) -> tuple[ResultadoTrayectoriaCapital, ResultadoExposicionCapital]:
    """Puente puro V3-D -> V3-C: trayectoria real y exposición resultante."""
    trayectoria = construir_trayectoria_capital_real(
        capital_inicial=capital_inicial,
        fecha_inicio_contrato=fecha_inicio_contrato,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        eventos=eventos_capital,
    )
    exposicion = calcular_exposicion_capital(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        capital_programado=capital_programado,
        capital_real=trayectoria.puntos,
        politica=politica_interes,
        referencia_resultado=referencia_resultado,
    )
    return trayectoria, exposicion


def _normalizar_eventos(
    eventos: Iterable[EventoReduccionCapital],
) -> tuple[EventoReduccionCapital, ...]:
    normalizados = tuple(sorted(eventos, key=lambda e: (e.fecha_valor, e.referencia or "")))
    for anterior, actual in zip(normalizados, normalizados[1:]):
        if (
            actual.fecha_valor == anterior.fecha_valor
            and actual.referencia
            and anterior.referencia
            and actual.referencia == anterior.referencia
        ):
            raise ErrorValidacion(
                "No puede haber dos eventos de capital con la misma fecha y referencia"
            )
    return normalizados


def _agrupar_por_fecha(
    eventos: Sequence[EventoReduccionCapital],
) -> tuple[tuple[date, tuple[EventoReduccionCapital, ...]], ...]:
    agrupados: list[tuple[date, tuple[EventoReduccionCapital, ...]]] = []
    for evento in eventos:
        if not agrupados or agrupados[-1][0] != evento.fecha_valor:
            agrupados.append((evento.fecha_valor, (evento,)))
        else:
            fecha, actuales = agrupados[-1]
            agrupados[-1] = (fecha, actuales + (evento,))
    return tuple(agrupados)


def _reducir_capital(capital: Decimal, evento: EventoReduccionCapital) -> Decimal:
    nuevo = money(capital - evento.monto)
    if nuevo < ZERO:
        raise ErrorInvariante(
            f"La reducción de capital {evento.monto} supera el capital real disponible {capital}"
        )
    return nuevo
