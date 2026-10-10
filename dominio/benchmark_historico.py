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

from .excepciones import ErrorCalculo, ErrorValidacion
from .tipos import money
from .xirr import xirr


DIAS_MINIMOS_SERIE_BENCHMARK = 30


@dataclass(frozen=True, slots=True)
class ObservacionIndiceRetornoTotal:
    """Nivel observado de un índice total-return en una moneda declarada."""

    fecha: date
    nivel_indice: Decimal
    moneda: str
    fuente: str
    tipo_indice: str
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
        if not isinstance(self.tipo_indice, str) or self.tipo_indice.strip().upper() not in {
            "BRUTO_TOTAL_RETURN",
            "NETO_TOTAL_RETURN",
        }:
            raise ErrorValidacion(
                "El tipo de índice debe ser BRUTO_TOTAL_RETURN o NETO_TOTAL_RETURN"
            )
        if self.referencia is not None and not isinstance(self.referencia, str):
            raise ErrorValidacion("La referencia de la observación debe ser texto")
        object.__setattr__(self, "moneda", self.moneda.strip().upper())
        object.__setattr__(self, "fuente", self.fuente.strip())
        object.__setattr__(self, "tipo_indice", self.tipo_indice.strip().upper())
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
    tipo_indice: str
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
    tipo_indice = serie[0].tipo_indice
    fecha_anterior: date | None = None
    for observacion in serie:
        if observacion.moneda != moneda:
            raise ErrorValidacion(
                "La serie mezcla monedas; separá las monedas o convertí la serie "
                "con una fuente de tipo de cambio identificada."
            )
        if observacion.tipo_indice != tipo_indice:
            raise ErrorValidacion(
                "La serie mezcla índices brutos/netos; usá una metodología homogénea."
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


@dataclass(frozen=True, slots=True)
class ResultadoBacktestIndiceRetornoTotal:
    """Valoración histórica de capital y cuotas sobre un índice observado."""

    fecha_inicio_operacion: date
    fecha_fin_operacion: date
    fecha_observacion_inicio: date
    fecha_observacion_fin: date
    dias_desfase_inicio: int
    dias_desfase_fin: int
    moneda: str
    tipo_indice: str
    cantidad_observaciones: int
    capital_inicial_usd: Decimal
    cantidad_flujos: int
    valor_final_capital_original: Decimal
    valor_final_cuotas_reinvertidas: Decimal
    brecha_final: Decimal
    rendimiento_anualizado_capital_original: Decimal
    xirr_cartera_reinvertida: Decimal | None


def _observacion_asof(
    serie: tuple[ObservacionIndiceRetornoTotal, ...],
    fecha: date,
    *,
    desfase_maximo_dias: int,
) -> tuple[ObservacionIndiceRetornoTotal, int]:
    """Busca el último cierre observado igual o anterior a la fecha solicitada."""
    if fecha < serie[0].fecha or fecha > serie[-1].fecha:
        raise ErrorValidacion(
            f"La fecha {fecha.isoformat()} queda fuera de la cobertura histórica "
            f"({serie[0].fecha.isoformat()} a {serie[-1].fecha.isoformat()}); "
            "no se extrapolan datos."
        )
    elegida = None
    for observacion in serie:
        if observacion.fecha > fecha:
            break
        elegida = observacion
    if elegida is None:
        raise ErrorValidacion(
            f"No hay una observación histórica igual o anterior a {fecha.isoformat()}."
        )
    desfase = (fecha - elegida.fecha).days
    if desfase > desfase_maximo_dias:
        raise ErrorValidacion(
            f"La última observación previa a {fecha.isoformat()} tiene {desfase} días; "
            f"el máximo admitido es {desfase_maximo_dias}. No se usa un dato obsoleto."
        )
    return elegida, desfase


def comparar_flujos_con_indice_historico(
    *,
    capital_inicial_usd: Decimal,
    fecha_desembolso: date,
    flujos_cuotas: Sequence[tuple[date, Decimal]],
    observaciones: Sequence[ObservacionIndiceRetornoTotal],
    desfase_maximo_dias: int = 45,
) -> ResultadoBacktestIndiceRetornoTotal:
    """Valúa el capital y las cuotas reinvertidas en un índice histórico observado.

    Se compara el valor del capital inicial mantenido invertido con el valor que
    habrían alcanzado las cuotas al reinvertirse en la fecha programada. Cada
    flujo se valúa usando el último índice observado igual o anterior a su fecha,
    con tolerancia máxima de desfase. El backtest usa exclusivamente fechas
    cubiertas por la serie y no aplica de nuevo costos/impuestos a los niveles:
    su efecto depende de si la fuente está marcada bruta o neta.
    """
    serie = validar_serie_indice_retorno_total(observaciones)
    if serie[0].moneda != "USD":
        raise ErrorValidacion(
            "El backtest de este plan requiere un índice expresado en USD."
        )
    if not isinstance(capital_inicial_usd, Decimal) or not capital_inicial_usd.is_finite():
        raise ErrorValidacion("El capital inicial debe ser un Decimal finito.")
    if capital_inicial_usd <= 0:
        raise ErrorValidacion("El capital inicial debe ser mayor a cero.")
    if not isinstance(fecha_desembolso, date):
        raise ErrorValidacion("La fecha de desembolso debe ser una fecha válida.")
    if not isinstance(desfase_maximo_dias, int) or desfase_maximo_dias < 0:
        raise ErrorValidacion("El desfase máximo debe ser un entero no negativo.")
    if not flujos_cuotas:
        raise ErrorValidacion("Se necesitan flujos de cuotas para el backtest histórico.")

    flujos: list[tuple[date, Decimal]] = []
    for flujo in flujos_cuotas:
        try:
            fecha, importe = flujo
        except (TypeError, ValueError) as exc:
            raise ErrorValidacion(
                "Cada flujo debe contener fecha e importe."
            ) from exc
        if not isinstance(fecha, date) or fecha <= fecha_desembolso:
            raise ErrorValidacion(
                "Cada cuota debe tener una fecha posterior al desembolso."
            )
        if not isinstance(importe, Decimal) or not importe.is_finite() or importe <= 0:
            raise ErrorValidacion(
                "Cada cuota para reinvertir debe ser un Decimal finito mayor a cero."
            )
        flujos.append((fecha, importe))

    fecha_final = max(fecha for fecha, _ in flujos)
    dias_operacion = (fecha_final - fecha_desembolso).days
    if dias_operacion <= 0:
        raise ErrorValidacion(
            "El período histórico debe ser mayor a cero días."
        )

    observacion_inicio, desfase_inicio = _observacion_asof(
        serie, fecha_desembolso, desfase_maximo_dias=desfase_maximo_dias
    )
    observacion_fin, desfase_fin = _observacion_asof(
        serie, fecha_final, desfase_maximo_dias=desfase_maximo_dias
    )
    if observacion_fin.fecha <= observacion_inicio.fecha:
        raise ErrorValidacion(
            "La serie no contiene dos cierres observados distintos para el horizonte del backtest."
        )

    niveles_por_fecha: dict[date, ObservacionIndiceRetornoTotal] = {
        observacion.fecha: observacion for observacion in serie
    }
    for fecha, _ in flujos:
        observacion_flujo, _ = _observacion_asof(
            serie, fecha, desfase_maximo_dias=desfase_maximo_dias
        )
        niveles_por_fecha[fecha] = observacion_flujo

    with localcontext() as contexto:
        contexto.prec = 40
        nivel_inicio = observacion_inicio.nivel_indice
        nivel_fin = observacion_fin.nivel_indice
        valor_capital_final = money(
            capital_inicial_usd * nivel_fin / nivel_inicio
        )
        valor_cuotas_final = money(
            sum(
                (
                    importe
                    * nivel_fin
                    / niveles_por_fecha[fecha].nivel_indice
                    for fecha, importe in flujos
                ),
                Decimal("0"),
            )
        )
        rendimiento_capital = contexto.power(
            nivel_fin / nivel_inicio,
            Decimal("365") / Decimal(dias_operacion),
        ) - Decimal("1")
    valor_capital_final = money(valor_capital_final)
    valor_cuotas_final = money(valor_cuotas_final)
    brecha = money(valor_cuotas_final - valor_capital_final)

    flujos_inversion = [(fecha_desembolso, -capital_inicial_usd)]
    flujos_inversion.extend((fecha, -importe) for fecha, importe in flujos)
    valor_cartera_final = money(valor_capital_final + valor_cuotas_final)
    flujos_inversion.append((fecha_final, valor_cartera_final))
    try:
        rendimiento_cartera = xirr(flujos_inversion)
    except (ErrorCalculo, ErrorValidacion, ArithmeticError, OverflowError):
        rendimiento_cartera = None

    return ResultadoBacktestIndiceRetornoTotal(
        fecha_inicio_operacion=fecha_desembolso,
        fecha_fin_operacion=fecha_final,
        fecha_observacion_inicio=observacion_inicio.fecha,
        fecha_observacion_fin=observacion_fin.fecha,
        dias_desfase_inicio=desfase_inicio,
        dias_desfase_fin=desfase_fin,
        moneda=serie[0].moneda,
        tipo_indice=serie[0].tipo_indice,
        cantidad_observaciones=len(serie),
        capital_inicial_usd=capital_inicial_usd,
        cantidad_flujos=len(flujos),
        valor_final_capital_original=valor_capital_final,
        valor_final_cuotas_reinvertidas=valor_cuotas_final,
        brecha_final=brecha,
        rendimiento_anualizado_capital_original=rendimiento_capital,
        xirr_cartera_reinvertida=rendimiento_cartera,
    )


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
        tipo_indice=inicio.tipo_indice,
        nivel_inicial=inicio.nivel_indice,
        nivel_final=fin.nivel_indice,
        rendimiento_acumulado=rendimiento_acumulado,
        rendimiento_anualizado=rendimiento_anualizado,
        caida_maxima=caida_maxima,
    )
