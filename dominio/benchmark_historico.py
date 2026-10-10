"""Validación y resumen de series históricas de índice de retorno total.

Esta capa trabaja con valores observados aportados por el usuario. No descarga
precios ni convierte series de precio simple en retorno total: el proveedor del
índice debe documentar que incluye las distribuciones/cupones reinvertidos.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from typing import Sequence

from .excepciones import ErrorValidacion


DIAS_MINIMOS_SERIE_BENCHMARK = 30


@dataclass(frozen=True, slots=True)
class ObservacionIndiceRetornoTotal:
    """Nivel observado de un índice total-return en una moneda declarada."""

    fecha: date
    nivel_indice: Decimal
    moneda: str
    fuente: str
    referencia: str | None = None

    def __post_init__(self) -> None:
        if type(self.fecha) is not date:
            raise ErrorValidacion("La fecha de la observación debe tener formato de fecha")
        if not isinstance(self.nivel_indice, Decimal):
            raise ErrorValidacion("El nivel del índice debe representarse con Decimal")
        if not self.nivel_indice.is_finite() or self.nivel_indice <= 0:
            raise ErrorValidacion("El nivel del índice debe ser un Decimal finito mayor a cero")
        if not isinstance(self.moneda, str) or not self.moneda.strip():
            raise ErrorValidacion("La moneda de la serie es obligatoria")
        if not isinstance(self.fuente, str) or not self.fuente.strip():
            raise ErrorValidacion("La fuente de cada observación es obligatoria")
        if self.referencia is not None and not isinstance(self.referencia, str):
            raise ErrorValidacion("La referencia de la observación debe ser texto")
        object.__setattr__(self, "moneda", self.moneda.strip().upper())
        object.__setattr__(self, "fuente", self.fuente.strip())
        if self.referencia is not None:
            referencia = self.referencia.strip()
            object.__setattr__(self, "referencia", referencia or None)


@dataclass(frozen=True, slots=True)
class ResumenSerieIndiceRetornoTotal:
    """Estadísticas históricas observadas; no constituyen un pronóstico."""

    fecha_inicio: date
    fecha_fin: date
    dias_transcurridos: int
    cantidad_observaciones: int
    moneda: str
    nivel_inicial: Decimal
    nivel_final: Decimal
    rendimiento_acumulado: Decimal
    rendimiento_anualizado: Decimal
    caida_maxima: Decimal


def validar_serie_indice_retorno_total(
    observaciones: Sequence[ObservacionIndiceRetornoTotal],
) -> tuple[ObservacionIndiceRetornoTotal, ...]:
    """Valida una serie homogénea y estrictamente cronológica de dos o más puntos."""
    if isinstance(observaciones, (str, bytes)):
        raise ErrorValidacion("La serie debe ser una colección de observaciones")
    try:
        serie = tuple(observaciones)
    except TypeError as exc:
        raise ErrorValidacion("La serie debe ser una colección de observaciones") from exc

    if len(serie) < 2:
        raise ErrorValidacion("La serie histórica necesita al menos dos observaciones")
    if not all(isinstance(item, ObservacionIndiceRetornoTotal) for item in serie):
        raise ErrorValidacion(
            "Todas las filas deben ser observaciones válidas de índice de retorno total"
        )

    moneda = serie[0].moneda
    fecha_anterior: date | None = None
    for observacion in serie:
        if observacion.moneda != moneda:
            raise ErrorValidacion(
                "La serie mezcla monedas; separá las monedas o convertí la serie "
                "con una fuente de tipo de cambio identificada."
            )
        if fecha_anterior is not None and observacion.fecha <= fecha_anterior:
            raise ErrorValidacion(
                "Las fechas deben estar ordenadas de menor a mayor y no repetirse."
            )
        fecha_anterior = observacion.fecha

    dias = (serie[-1].fecha - serie[0].fecha).days
    if dias < DIAS_MINIMOS_SERIE_BENCHMARK:
        raise ErrorValidacion(
            f"La serie debe cubrir al menos {DIAS_MINIMOS_SERIE_BENCHMARK} días "
                       "para calcular rendimiento anualizado."
        )
    return serie


def resumir_serie_indice_retorno_total(
    observaciones: Sequence[ObservacionIndiceRetornoTotal],
) -> ResumenSerieIndiceRetornoTotal:
    """Calcula retorno acumulado, CAGR observado y caída máxima desde el pico.

    La tasa anualizada utiliza base 365 días y niveles de un índice de retorno
    total. No representa una rentabilidad garantizada futura ni una tasa neta
    después de costos/impuestos: esos supuestos se calculan por separado.
    """
    serie = validar_serie_indice_retorno_total(observaciones)
    inicio, fin = serie[0], serie[-1]
    dias = (fin.fecha - inicio.fecha).days

    with localcontext() as contexto:
        contexto.prec = 40
        factor_total = fin.nivel_indice / inicio.nivel_indice
        rendimiento_acumulado = factor_total - Decimal("1")
        rendimiento_anualizado = contexto.power(
            factor_total,
            Decimal("365") / Decimal(dias),
        ) - Decimal("1")

        maximo_historico = inicio.nivel_indice
        caida_maxima = Decimal("0")
        for observacion in serie:
            if observacion.nivel_indice > maximo_historico:
                maximo_historico = observacion.nivel_indice
            caida_desde_pico = (
                observacion.nivel_indice / maximo_historico
            ) - Decimal("1")
            if caida_desde_pico < caida_maxima:
                caida_maxima = caida_desde_pico

    return ResumenSerieIndiceRetornoTotal(
        fecha_inicio=inicio.fecha,
        fecha_fin=fin.fecha,
        dias_transcurridos=dias,
        cantidad_observaciones=len(serie),
        moneda=inicio.moneda,
        nivel_inicial=inicio.nivel_indice,
        nivel_final=fin.nivel_indice,
        rendimiento_acumulado=rendimiento_acumulado,
        rendimiento_anualizado=rendimiento_anualizado,
        caida_maxima=caida_maxima,
    )
