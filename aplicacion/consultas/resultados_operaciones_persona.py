"""Resultados efectivos por operación para una persona.

Agrupa los flujos reales que ya construye AnalisisFinancieroQuery. No accede a
SQLite, no recalcula amortizaciones y no mezcla operaciones distintas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aplicacion.consultas.analisis_financiero import (
    AnalisisFinancieroQuery,
    FlujoCajaFinanciero,
)
from aplicacion.puertos.persona_financiera import ConsultaExistenciaPersonaFinanciera
from dominio.analisis_cambiario import calcular_rendimiento_real
from dominio.excepciones import ErrorCalculo, ErrorValidacion
from dominio.xirr import xirr

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class ResultadoOperacionPersona:
    """Métricas y evidencia de una operación desde un único rol."""

    prestamo_id: int
    prestamo_numero: str
    rol: str
    fecha_inicio: date | None
    fecha_fin: date | None
    flujos_reales: tuple[FlujoCajaFinanciero, ...]
    xirr_anual: Decimal | None
    xirr_usd_anual: Decimal | None
    rendimiento_real_anual: Decimal | None
    evidencia_suficiente: bool
    motivo_no_disponible: str | None

    @property
    def metrica_nombre(self) -> str:
        return "Rendimiento efectivo" if self.rol == "inversor" else "Costo efectivo"

    @property
    def tiene_usd_completo(self) -> bool:
        return bool(self.flujos_reales) and all(
            flujo.monto_usd is not None for flujo in self.flujos_reales
        )

    @property
    def cantidad_flujos(self) -> int:
        return len(self.flujos_reales)


@dataclass(frozen=True)
class ResultadosOperacionesPersona:
    """Vista de todas las operaciones identificables de una persona."""

    persona_id: int
    fecha_corte: date
    inflacion_mensual_supuesta: Decimal
    operaciones: tuple[ResultadoOperacionPersona, ...]
    advertencias: tuple[str, ...]

    @property
    def disponibles(self) -> tuple[ResultadoOperacionPersona, ...]:
        return tuple(
            operacion
            for operacion in self.operaciones
            if operacion.evidencia_suficiente
        )

    @property
    def sin_calculo(self) -> tuple[ResultadoOperacionPersona, ...]:
        return tuple(
            operacion
            for operacion in self.operaciones
            if not operacion.evidencia_suficiente
        )


class ResultadosOperacionesPersonaQuery:
    """Construye resultados por operación a partir de hechos reales."""

    def __init__(
        self,
        *,
        personas: ConsultaExistenciaPersonaFinanciera,
        analisis: AnalisisFinancieroQuery,
    ) -> None:
        self._personas = personas
        self._analisis = analisis

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        inflacion_mensual_supuesta: Decimal = Decimal("0.05"),
    ) -> ResultadosOperacionesPersona:
        if persona_id <= 0:
            raise ValueError("persona_id debe ser positivo")
        if not self._personas.existe(persona_id):
            raise ValueError(f"La persona {persona_id} no existe")

        corte = fecha_corte or date.today()
        inflacion = Decimal(str(inflacion_mensual_supuesta))
        if not inflacion.is_finite() or inflacion <= Decimal("-1"):
            raise ValueError("La inflación mensual debe ser finita y mayor a -100%")

        analisis = self._analisis.obtener(
            persona_id,
            fecha_corte=corte,
            inflacion_mensual_supuesto=inflacion,
            incluir_operaciones_cerradas=True,
        )
        inflacion_anual = (Decimal("1") + inflacion) ** 12 - Decimal("1")

        grupos: dict[tuple[int, str], list[FlujoCajaFinanciero]] = {}
        for flujo in analisis.flujos_reales:
            if (
                not flujo.real
                or flujo.prestamo_id <= 0
                or flujo.rol not in {"inversor", "deudor"}
            ):
                continue
            grupos.setdefault((flujo.prestamo_id, flujo.rol), []).append(flujo)

        ordenados = sorted(
            grupos.items(),
            key=lambda item: (
                max(flujo.fecha for flujo in item[1]),
                item[0][0],
                item[0][1],
            ),
            reverse=True,
        )
        operaciones: list[ResultadoOperacionPersona] = []
        for (prestamo_id, rol), flujos in ordenados:
            flujos_ordenados = tuple(
                sorted(flujos, key=lambda flujo: (flujo.fecha, flujo.tipo, flujo.origen))
            )
            tasa, motivo = _calcular_tasa(
                (flujo.fecha, flujo.monto_ars) for flujo in flujos_ordenados
            )
            tasa_usd, _ = _calcular_tasa_usd(flujos_ordenados)
            rendimiento_real = (
                calcular_rendimiento_real(tasa, inflacion_anual)
                if tasa is not None
                else None
            )
            primero = flujos_ordenados[0]
            operaciones.append(
                ResultadoOperacionPersona(
                    prestamo_id=prestamo_id,
                    prestamo_numero=primero.prestamo_numero or f"#{prestamo_id}",
                    rol=rol,
                    fecha_inicio=flujos_ordenados[0].fecha,
                    fecha_fin=flujos_ordenados[-1].fecha,
                    flujos_reales=flujos_ordenados,
                    xirr_anual=tasa,
                    xirr_usd_anual=tasa_usd,
                    rendimiento_real_anual=rendimiento_real,
                    evidencia_suficiente=tasa is not None,
                    motivo_no_disponible=motivo,
                )
            )

        return ResultadosOperacionesPersona(
            persona_id=persona_id,
            fecha_corte=corte,
            inflacion_mensual_supuesta=inflacion,
            operaciones=tuple(operaciones),
            advertencias=analisis.advertencias,
        )


class ServicioResultadosOperacionesPersona:
    """Caso de uso de lectura para la pantalla de rendimiento."""

    def __init__(self, query: ResultadosOperacionesPersonaQuery) -> None:
        self._query = query

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        inflacion_mensual_supuesta: Decimal = Decimal("0.05"),
    ) -> ResultadosOperacionesPersona:
        return self._query.obtener(
            persona_id,
            fecha_corte=fecha_corte,
            inflacion_mensual_supuesta=inflacion_mensual_supuesta,
        )


def _netos_por_fecha(
    flujos,
) -> list[tuple[date, Decimal]]:
    """Compensa movimientos de una misma fecha antes de evaluar los signos."""
    netos: dict[date, Decimal] = {}
    for fecha, monto in flujos:
        if monto is None or not monto.is_finite():
            continue
        netos[fecha] = netos.get(fecha, ZERO) + monto
    return [
        (fecha, monto)
        for fecha, monto in sorted(netos.items())
        if monto != ZERO
    ]


def _resolver_xirr(
    flujos,
    *,
    evidencia_usd: bool = False,
) -> tuple[Decimal | None, str | None]:
    netos = _netos_por_fecha(flujos)
    moneda = "USD" if evidencia_usd else "ARS"
    if len(netos) < 2:
        return (
            None,
            f"Todavía no hay al menos dos fechas con movimientos netos en {moneda}.",
        )

    signos = {monto > ZERO for _, monto in netos}
    if len(signos) < 2:
        return (
            None,
            f"Todavía no hay movimientos reales de entrada y salida en {moneda}.",
        )

    try:
        return xirr(netos), None
    except ErrorValidacion as exc:
        if "alternan de signo" in str(exc).lower():
            return (
                None,
                "Los movimientos alternan de signo más de una vez; no se informa "
                "una tasa única porque la XIRR podría ser ambigua.",
            )
        return (
            None,
            f"Los movimientos existen, pero no permiten una XIRR válida en {moneda}.",
        )
    except ErrorCalculo:
        return (
            None,
            f"No se encontró una XIRR dentro del rango numérico admitido en {moneda}.",
        )


def _calcular_tasa(flujos) -> tuple[Decimal | None, str | None]:
    """Calcula la tasa ARS sobre los flujos reales de una única operación."""
    return _resolver_xirr(flujos)


def _calcular_tasa_usd(
    flujos: tuple[FlujoCajaFinanciero, ...],
) -> tuple[Decimal | None, str | None]:
    """Calcula USD solo cuando todos los movimientos tienen conversión conocida."""
    if not flujos or any(flujo.monto_usd is None for flujo in flujos):
        return None, "Falta la conversión USD de uno o más movimientos reales."
    return _resolver_xirr(
        ((flujo.fecha, flujo.monto_usd) for flujo in flujos),
        evidencia_usd=True,
    )


__all__ = [
    "ResultadoOperacionPersona",
    "ResultadosOperacionesPersona",
    "ResultadosOperacionesPersonaQuery",
    "ServicioResultadosOperacionesPersona",
]
