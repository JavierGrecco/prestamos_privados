"""Read model de planificación financiera personal.

La planificación usa únicamente flujos futuros que ya conoce el sistema.
No inventa ingresos ni gastos externos y no modifica reglas financieras.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from aplicacion.consultas.analisis_financiero import (
    AnalisisFinancieroQuery,
    FlujoCajaFinanciero,
)
from dominio.tipos import money
from infraestructura.db import BaseDatos
from infraestructura.repositorios import PersonaRepo

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class PlanMensual:
    """Plan de movimientos previstos para un mes."""

    periodo: date
    cobros_estimados: Decimal
    pagos_estimados: Decimal
    neto_estimado: Decimal
    acumulado_estimado: Decimal

    @property
    def requiere_reserva(self) -> bool:
        return self.acumulado_estimado < ZERO


@dataclass(frozen=True)
class PlanificacionFinancieraPersona:
    """Plan de caja conocido para un horizonte determinado."""

    persona_id: int
    fecha_corte: date
    horizonte_meses: int
    fecha_fin: date
    cobros_estimados_total: Decimal
    pagos_estimados_total: Decimal
    neto_estimado_total: Decimal
    reserva_sugerida: Decimal
    mes_mas_exigente: PlanMensual | None
    movimientos_mensuales: tuple[PlanMensual, ...]

    @property
    def tiene_cobros(self) -> bool:
        return self.cobros_estimados_total > ZERO

    @property
    def tiene_pagos(self) -> bool:
        return self.pagos_estimados_total > ZERO

    @property
    def termina_con_superavit(self) -> bool:
        return self.neto_estimado_total >= ZERO


class PlanificacionFinancieraPersonaQuery:
    """Construye un plan futuro sin agregar supuestos externos."""

    def __init__(self, db: BaseDatos) -> None:
        self._personas = PersonaRepo(db)
        self._analisis = AnalisisFinancieroQuery(db)

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        horizonte_meses: int = 12,
    ) -> PlanificacionFinancieraPersona:
        if persona_id <= 0:
            raise ValueError("persona_id debe ser positivo")
        if horizonte_meses < 1 or horizonte_meses > 60:
            raise ValueError("horizonte_meses debe estar entre 1 y 60")

        persona = self._personas.obtener(persona_id)
        if persona is None:
            raise ValueError(f"La persona {persona_id} no existe")

        corte = fecha_corte or date.today()
        analisis = self._analisis.obtener(persona_id, fecha_corte=corte)

        futuros = tuple(
            flujo
            for flujo in analisis.flujos_proyectados
            if flujo.fecha > corte
        )

        fin = _fin_horizonte(corte, horizonte_meses)
        futuros = tuple(f for f in futuros if f.fecha <= fin)

        movimientos = _agrupar_por_mes(futuros, corte, horizonte_meses)
        cobros = money(sum((m.cobros_estimados for m in movimientos), ZERO))
        pagos = money(sum((m.pagos_estimados for m in movimientos), ZERO))
        neto = money(cobros - pagos)

        reserva = money(
            max(
                ZERO,
                -min((m.acumulado_estimado for m in movimientos), default=ZERO),
            )
        )

        mes_mas_exigente = (
            min(movimientos, key=lambda m: m.neto_estimado)
            if movimientos
            else None
        )

        return PlanificacionFinancieraPersona(
            persona_id=persona_id,
            fecha_corte=corte,
            horizonte_meses=horizonte_meses,
            fecha_fin=fin,
            cobros_estimados_total=cobros,
            pagos_estimados_total=pagos,
            neto_estimado_total=neto,
            reserva_sugerida=reserva,
            mes_mas_exigente=mes_mas_exigente,
            movimientos_mensuales=movimientos,
        )


class ServicioPlanificacionFinancieraPersona:
    """Caso de uso de lectura para planificación."""

    def __init__(self, db: BaseDatos) -> None:
        self._query = PlanificacionFinancieraPersonaQuery(db)

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        horizonte_meses: int = 12,
    ) -> PlanificacionFinancieraPersona:
        return self._query.obtener(
            persona_id,
            fecha_corte=fecha_corte,
            horizonte_meses=horizonte_meses,
        )


def _primer_dia_mes(fecha: date) -> date:
    return date(fecha.year, fecha.month, 1)


def _sumar_meses(fecha: date, cantidad: int) -> date:
    indice = fecha.year * 12 + fecha.month - 1 + cantidad
    return date(indice // 12, indice % 12 + 1, 1)


def _fin_horizonte(corte: date, horizonte_meses: int) -> date:
    primer_mes_siguiente = _sumar_meses(
        _primer_dia_mes(corte),
        horizonte_meses + 1,
    )
    return primer_mes_siguiente - timedelta(days=1)


def _agrupar_por_mes(
    flujos: tuple[FlujoCajaFinanciero, ...],
    corte: date,
    horizonte_meses: int,
) -> tuple[PlanMensual, ...]:
    acumulado = ZERO
    resultado: list[PlanMensual] = []
    primer_mes = _sumar_meses(_primer_dia_mes(corte), 1)

    for offset in range(horizonte_meses):
        periodo = _sumar_meses(primer_mes, offset)
        siguiente = _sumar_meses(periodo, 1)
        del_mes = [
            flujo
            for flujo in flujos
            if periodo <= flujo.fecha < siguiente
        ]

        cobros = money(
            sum(
                (
                    flujo.monto_ars
                    for flujo in del_mes
                    if flujo.rol == "inversor" and flujo.monto_ars > ZERO
                ),
                ZERO,
            )
        )
        pagos = money(
            sum(
                (
                    -flujo.monto_ars
                    for flujo in del_mes
                    if flujo.rol == "deudor" and flujo.monto_ars < ZERO
                ),
                ZERO,
            )
        )
        neto = money(cobros - pagos)
        acumulado = money(acumulado + neto)

        resultado.append(
            PlanMensual(
                periodo=periodo,
                cobros_estimados=cobros,
                pagos_estimados=pagos,
                neto_estimado=neto,
                acumulado_estimado=acumulado,
            )
        )

    return tuple(resultado)
