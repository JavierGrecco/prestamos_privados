"""Resultados efectivos por operación para una persona.

Este read model reutiliza los flujos reales de AnalisisFinancieroQuery.
No recalcula amortizaciones ni inventa tasas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aplicacion.consultas.analisis_financiero import (
    AnalisisFinancieroQuery,
    FlujoCajaFinanciero,
)
from dominio.analisis_cambiario import calcular_rendimiento_real
from dominio.xirr import xirr
from dominio.tipos import money
from infraestructura.db import BaseDatos
from infraestructura.repositorios import PersonaRepo

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class ResultadoOperacionPersona:
    prestamo_id: int
    prestamo_numero: str
    destino: str
    rol: str
    fecha_inicio: date | None
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
    persona_id: int
    fecha_corte: date
    inflacion_mensual_supuesta: Decimal
    operaciones: tuple[ResultadoOperacionPersona, ...]

    @property
    def disponibles(self) -> tuple[ResultadoOperacionPersona, ...]:
        return tuple(o for o in self.operaciones if o.evidencia_suficiente)

    @property
    def sin_calculo(self) -> tuple[ResultadoOperacionPersona, ...]:
        return tuple(o for o in self.operaciones if not o.evidencia_suficiente)


class ResultadosOperacionesPersonaQuery:
    """Construye resultados por operación a partir de hechos reales."""

    def __init__(self, db: BaseDatos) -> None:
        self._db = db
        self._personas = PersonaRepo(db)
        self._analisis = AnalisisFinancieroQuery(db)

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        inflacion_mensual_supuesta: Decimal = Decimal("0.05"),
    ) -> ResultadosOperacionesPersona:
        if persona_id <= 0:
            raise ValueError("persona_id debe ser positivo")

        persona = self._personas.obtener(persona_id)
        if persona is None:
            raise ValueError(f"La persona {persona_id} no existe")

        corte = fecha_corte or date.today()
        inflacion = Decimal(str(inflacion_mensual_supuesta))
        if inflacion <= Decimal("-1"):
            raise ValueError("La inflación mensual debe ser mayor a -100%")

        analisis = self._analisis.obtener(
            persona_id,
            fecha_corte=corte,
            inflacion_mensual_supuesto=inflacion,
        )
        inflacion_anual = (Decimal("1") + inflacion) ** 12 - Decimal("1")

        grupos: dict[tuple[int, str], list[FlujoCajaFinanciero]] = {}
        for flujo in analisis.flujos_reales:
            if flujo.prestamo_id <= 0:
                continue
            grupos.setdefault((flujo.prestamo_id, flujo.rol), []).append(flujo)

        operaciones: list[ResultadoOperacionPersona] = []
        for (prestamo_id, rol), flujos in sorted(
            grupos.items(),
            key=lambda item: (
                item[1][0].fecha if item[1] else date.min,
                item[0][0],
                item[0][1],
            ),
            reverse=True,
        ):
            flujos_ordenados = tuple(sorted(flujos, key=lambda flujo: flujo.fecha))
            tasa, motivo = _calcular_tasa(flujos_ordenados)
            tasa_usd, _ = _calcular_tasa_usd(flujos_ordenados)
            real = (
                calcular_rendimiento_real(tasa, inflacion_anual)
                if tasa is not None
                else None
            )
            primero = flujos_ordenados[0] if flujos_ordenados else None

            operaciones.append(
                ResultadoOperacionPersona(
                    prestamo_id=prestamo_id,
                    prestamo_numero=primero.prestamo_numero if primero else "—",
                    destino=_destino(prestamo_id, self._db),
                    rol=rol,
                    fecha_inicio=_fecha_inicio(flujos_ordenados),
                    flujos_reales=flujos_ordenados,
                    xirr_anual=tasa,
                    xirr_usd_anual=tasa_usd,
                    rendimiento_real_anual=real,
                    evidencia_suficiente=tasa is not None,
                    motivo_no_disponible=motivo,
                )
            )

        return ResultadosOperacionesPersona(
            persona_id=persona_id,
            fecha_corte=corte,
            inflacion_mensual_supuesta=inflacion,
            operaciones=tuple(operaciones),
        )


class ServicioResultadosOperacionesPersona:
    """Caso de uso de lectura para mostrar resultados por operación."""

    def __init__(self, db: BaseDatos) -> None:
        self._query = ResultadosOperacionesPersonaQuery(db)

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


def _calcular_tasa(
    flujos: tuple[FlujoCajaFinanciero, ...],
) -> tuple[Decimal | None, str | None]:
    normalizados = [
        (flujo.fecha, flujo.monto_ars)
        for flujo in flujos
        if flujo.monto_ars != ZERO
    ]
    if len(normalizados) < 2:
        return None, "Todavía no hay al menos dos movimientos reales."

    signos = {monto > ZERO for _, monto in normalizados}
    if len(signos) < 2:
        return (
            None,
            "Todavía no hay movimientos reales en ambos sentidos.",
        )

    try:
        return xirr(normalizados), None
    except Exception:
        return (
            None,
            "Los movimientos existen, pero todavía no permiten resolver una tasa efectiva.",
        )


def _calcular_tasa_usd(
    flujos: tuple[FlujoCajaFinanciero, ...],
) -> tuple[Decimal | None, str | None]:
    if not flujos or any(flujo.monto_usd is None for flujo in flujos):
        return None, "Faltan conversiones USD en uno o más movimientos reales."

    normalizados = [
        (flujo.fecha, flujo.monto_usd)
        for flujo in flujos
        if flujo.monto_usd not in (None, ZERO)
    ]
    if len(normalizados) < 2:
        return None, "Todavía no hay suficientes movimientos USD."
    if not {monto > ZERO for _, monto in normalizados} == {True, False}:
        return None, "Todavía no hay movimientos USD en ambos sentidos."

    try:
        return xirr(normalizados), None
    except Exception:
        return None, "Los movimientos USD no permiten resolver una tasa efectiva."


def _fecha_inicio(flujos: tuple[FlujoCajaFinanciero, ...]) -> date | None:
    if not flujos:
        return None
    return min(flujo.fecha for flujo in flujos)


def _destino(prestamo_id: int, db: BaseDatos) -> str:
    fila = db.consultar_uno(
        "SELECT COALESCE(destino, '') AS destino FROM prestamos WHERE id = ?",
        (prestamo_id,),
    )
    if fila is None:
        return "Sin destino"
    destino = str(fila["destino"] or "").strip()
    return destino or "Sin destino"
