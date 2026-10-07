"""Motor puro V3-C para interés adicional por exceso de exposición de capital.

Este módulo NO registra pagos ni modifica el cronograma. Compara, por tramos
[fecha_desde, fecha_hasta), el capital que debería quedar según el cronograma
contractual contra el capital realmente pendiente y devenga interés únicamente
sobre la exposición adicional positiva.

La decisión de qué constituye "capital real" y cómo actualizarlo a partir de
pagos pertenece a la capa de aplicación. El motor recibe esa trayectoria ya
materializada y es completamente determinista.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable, Sequence

from .devengamiento_v3 import PoliticaInteres, calcular_devengamiento_interes
from .excepciones import ErrorInvariante, ErrorValidacion
from .motor_pagos_v3 import Devengamiento, ZERO
from .tipos import money


@dataclass(frozen=True)
class PuntoCapitalProgramado:
    """Capital contractual vigente desde ``fecha`` hasta el siguiente punto."""

    fecha: date
    capital: Decimal
    referencia: str | None = None

    def __post_init__(self) -> None:
        capital = money(self.capital)
        if capital < ZERO:
            raise ErrorValidacion("El capital programado no puede ser negativo")
        object.__setattr__(self, "capital", capital)


@dataclass(frozen=True)
class PuntoCapitalReal:
    """Capital efectivamente pendiente vigente desde ``fecha``."""

    fecha: date
    capital: Decimal
    referencia: str | None = None

    def __post_init__(self) -> None:
        capital = money(self.capital)
        if capital < ZERO:
            raise ErrorValidacion("El capital real no puede ser negativo")
        object.__setattr__(self, "capital", capital)


@dataclass(frozen=True)
class TramoExposicionCapital:
    """Estado y devengamiento de un tramo temporal."""

    fecha_desde: date
    fecha_hasta: date
    capital_programado: Decimal
    capital_real: Decimal
    exceso_capital: Decimal
    devengamiento: Devengamiento | None
    referencia_programada: str | None = None
    referencia_real: str | None = None

    def __post_init__(self) -> None:
        cp = money(self.capital_programado)
        cr = money(self.capital_real)
        exceso = money(self.exceso_capital)
        if self.fecha_hasta < self.fecha_desde:
            raise ErrorValidacion("El tramo tiene fechas inválidas")
        if cp < ZERO or cr < ZERO:
            raise ErrorValidacion("Los capitales de exposición no pueden ser negativos")
        esperado = money(cr - cp)
        if exceso != esperado:
            raise ErrorInvariante(
                f"Exceso inconsistente: esperado {esperado}, observado {exceso}"
            )
        if self.devengamiento is not None:
            if self.devengamiento.fecha_desde != self.fecha_desde:
                raise ErrorInvariante("El devengamiento no coincide con el inicio del tramo")
            if self.devengamiento.fecha_hasta != self.fecha_hasta:
                raise ErrorInvariante("El devengamiento no coincide con el fin del tramo")
            if self.exceso_capital <= ZERO and self.devengamiento.monto != ZERO:
                raise ErrorInvariante("No puede existir interés adicional con exceso no positivo")


@dataclass(frozen=True)
class ResultadoExposicionCapital:
    """Resultado completo y auditable del análisis de exposición."""

    fecha_desde: date
    fecha_hasta: date
    tramos: tuple[TramoExposicionCapital, ...]

    @property
    def interes_adicional_total(self) -> Decimal:
        return money(
            sum(
                (t.devengamiento.monto for t in self.tramos if t.devengamiento is not None),
                ZERO,
            )
        )

    @property
    def exposicion_maxima(self) -> Decimal:
        if not self.tramos:
            return ZERO
        return max((t.exceso_capital for t in self.tramos), default=ZERO)

    def validar(self) -> None:
        if self.fecha_hasta < self.fecha_desde:
            raise ErrorValidacion("El período de exposición es inválido")
        anterior: date | None = None
        for tramo in self.tramos:
            if tramo.fecha_hasta <= tramo.fecha_desde:
                raise ErrorInvariante("Un tramo debe tener duración positiva")
            if anterior is not None and tramo.fecha_desde != anterior:
                raise ErrorInvariante("Los tramos no son contiguos")
            anterior = tramo.fecha_hasta
            if tramo.exceso_capital > ZERO:
                if tramo.devengamiento is None:
                    raise ErrorInvariante("Falta devengamiento en un tramo con exceso")
            elif tramo.devengamiento is not None and tramo.devengamiento.monto != ZERO:
                raise ErrorInvariante("Existe interés adicional sin exceso de capital")
        if self.tramos:
            if self.tramos[0].fecha_desde != self.fecha_desde:
                raise ErrorInvariante("El primer tramo no coincide con el inicio solicitado")
            if self.tramos[-1].fecha_hasta != self.fecha_hasta:
                raise ErrorInvariante("El último tramo no coincide con el fin solicitado")


def calcular_exposicion_capital(
    *,
    fecha_desde: date,
    fecha_hasta: date,
    capital_programado: Sequence[PuntoCapitalProgramado],
    capital_real: Sequence[PuntoCapitalReal],
    politica: PoliticaInteres,
    referencia_resultado: str = "EXPOSICION_CAPITAL",
) -> ResultadoExposicionCapital:
    """Calcula interés adicional sólo sobre exceso positivo de capital.

    Semántica temporal: cada punto es efectivo desde ``fecha`` inclusive y
    permanece vigente hasta el siguiente punto. Las series pueden tener más
    puntos que el período solicitado, pero ambas deben aportar un punto de
    referencia vigente en ``fecha_desde``.

    Si el capital real es menor que el programado, el exceso es negativo y no
    se genera interés adicional. El módulo no interpreta esa diferencia como
    una aplicación de prepago: eso pertenece a otra decisión del motor.
    """
    if fecha_hasta < fecha_desde:
        raise ErrorValidacion("La fecha hasta no puede ser anterior a la fecha desde")
    if fecha_hasta == fecha_desde:
        return ResultadoExposicionCapital(fecha_desde, fecha_hasta, ())

    programado = _normalizar_puntos(capital_programado, "programado")
    real = _normalizar_puntos(capital_real, "real")
    _exigir_punto_inicial(programado, fecha_desde, "capital programado")
    _exigir_punto_inicial(real, fecha_desde, "capital real")

    eventos = {fecha_desde, fecha_hasta}
    eventos.update(p.fecha for p in programado if fecha_desde < p.fecha < fecha_hasta)
    eventos.update(p.fecha for p in real if fecha_desde < p.fecha < fecha_hasta)
    fechas = sorted(eventos)

    tramos: list[TramoExposicionCapital] = []
    for inicio, fin in zip(fechas, fechas[1:]):
        ref = _punto_vigente(programado, inicio)
        act = _punto_vigente(real, inicio)
        exceso = money(act.capital - ref.capital)

        devengamiento = None
        if exceso > ZERO:
            devengamiento = calcular_devengamiento_interes(
                base=exceso,
                fecha_desde=inicio,
                fecha_hasta=fin,
                politica=politica,
                referencia=f"{referencia_resultado}:{inicio.isoformat()}:{fin.isoformat()}",
            )

        tramos.append(
            TramoExposicionCapital(
                fecha_desde=inicio,
                fecha_hasta=fin,
                capital_programado=ref.capital,
                capital_real=act.capital,
                exceso_capital=exceso,
                devengamiento=devengamiento,
                referencia_programada=ref.referencia,
                referencia_real=act.referencia,
            )
        )

    resultado = ResultadoExposicionCapital(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        tramos=tuple(tramos),
    )
    resultado.validar()
    return resultado


def puntos_programados_desde_tabla(
    *, fecha_inicio: date, capital_inicial: Decimal, tabla: Iterable[dict]
) -> tuple[PuntoCapitalProgramado, ...]:
    """Adapta una tabla de amortización materializada al contrato del V3-C.

    La tabla existente del proyecto expone ``capital_inicial``, ``saldo`` y
    ``vencimiento``. El saldo posterior a cada vencimiento pasa a ser el
    capital contractual vigente desde ese día.
    """
    filas = list(tabla)
    if not filas:
        raise ErrorValidacion("La tabla de amortización no puede estar vacía")

    puntos: list[PuntoCapitalProgramado] = [
        PuntoCapitalProgramado(
            fecha=fecha_inicio,
            capital=capital_inicial,
            referencia="INICIO_CONTRATO",
        )
    ]
    for fila in filas:
        try:
            vencimiento = fila["vencimiento"]
            saldo = fila["saldo"]
            numero = fila["numero"]
        except KeyError as exc:
            raise ErrorValidacion(f"La fila de amortización no contiene {exc.args[0]}") from exc
        if not isinstance(vencimiento, date):
            raise ErrorValidacion(f"Vencimiento inválido en cuota {numero}")
        puntos.append(
            PuntoCapitalProgramado(
                fecha=vencimiento,
                capital=saldo,
                referencia=f"CUOTA_{numero}_POSTERIOR",
            )
        )
    return tuple(puntos)


def _normalizar_puntos(
    puntos: Sequence[PuntoCapitalProgramado | PuntoCapitalReal], nombre: str
) -> tuple[PuntoCapitalProgramado | PuntoCapitalReal, ...]:
    if not puntos:
        raise ErrorValidacion(f"La serie de capital {nombre} no puede estar vacía")
    ordenados = tuple(sorted(puntos, key=lambda p: p.fecha))
    for anterior, actual in zip(ordenados, ordenados[1:]):
        if actual.fecha == anterior.fecha:
            raise ErrorValidacion(
                f"La serie de capital {nombre} contiene dos puntos en {actual.fecha}"
            )
    return ordenados


def _exigir_punto_inicial(
    puntos: Sequence[PuntoCapitalProgramado | PuntoCapitalReal],
    fecha: date,
    nombre: str,
) -> None:
    if puntos[0].fecha > fecha:
        raise ErrorValidacion(
            f"La serie de {nombre} no tiene un punto vigente al inicio del período"
        )


def _punto_vigente(
    puntos: Sequence[PuntoCapitalProgramado | PuntoCapitalReal], fecha: date
) -> PuntoCapitalProgramado | PuntoCapitalReal:
    vigente = None
    for punto in puntos:
        if punto.fecha <= fecha:
            vigente = punto
        else:
            break
    if vigente is None:
        raise ErrorInvariante(f"No existe punto vigente para {fecha}")
    return vigente
