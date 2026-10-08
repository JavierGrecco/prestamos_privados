"""Read model de posición financiera consolidada de una persona.

No representa el patrimonio total de la persona. Representa solamente la
posición que puede explicarse con los préstamos e inversiones registrados en
Préstamos Privados.

No escribe en SQLite ni redefine reglas financieras.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aplicacion.consultas.analisis_financiero import AnalisisFinancieroQuery, FlujoCajaFinanciero
from dominio.tipos import money
from infraestructura.db import BaseDatos
from infraestructura.repositorios import PersonaRepo

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class MovimientoMensualReal:
    """Resumen mensual de movimientos que ya ocurrieron."""

    periodo: date
    entradas: Decimal
    salidas: Decimal
    neto: Decimal
    acumulado: Decimal


@dataclass(frozen=True)
class PosicionFinancieraPersona:
    """Posición financiera conocida dentro de la aplicación."""

    persona_id: int
    fecha_corte: date
    capital_invertido: Decimal
    capital_deuda_pendiente: Decimal
    posicion_neta_capital: Decimal
    cobros_reales: Decimal
    pagos_reales: Decimal
    flujo_neto_real: Decimal
    cobros_futuros_estimados: Decimal
    pagos_futuros_estimados: Decimal
    flujo_neto_futuro_estimado: Decimal
    movimientos_mensuales: tuple[MovimientoMensualReal, ...]

    @property
    def tiene_inversiones(self) -> bool:
        return self.capital_invertido > ZERO

    @property
    def tiene_deuda(self) -> bool:
        return self.capital_deuda_pendiente > ZERO

    @property
    def posicion_neta_es_positiva(self) -> bool:
        return self.posicion_neta_capital >= ZERO


class PosicionFinancieraPersonaQuery:
    """Construye la posición consolidada sin inventar activos externos."""

    def __init__(self, db: BaseDatos) -> None:
        self._personas = PersonaRepo(db)
        self._analisis = AnalisisFinancieroQuery(db)

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        meses_historicos: int = 12,
    ) -> PosicionFinancieraPersona:
        if persona_id <= 0:
            raise ValueError("persona_id debe ser positivo")
        if meses_historicos <= 0 or meses_historicos > 120:
            raise ValueError("meses_historicos debe estar entre 1 y 120")

        persona = self._personas.obtener(persona_id)
        if persona is None:
            raise ValueError(f"La persona {persona_id} no existe")

        corte = fecha_corte or date.today()
        analisis = self._analisis.obtener(persona_id, fecha_corte=corte)

        cobros_reales = sum(
            (
                f.monto_ars
                for f in analisis.flujos_reales
                if f.rol == "inversor" and f.monto_ars > ZERO
            ),
            ZERO,
        )
        pagos_reales = sum(
            (
                -f.monto_ars
                for f in analisis.flujos_reales
                if f.rol == "deudor" and f.monto_ars < ZERO
            ),
            ZERO,
        )

        cobros_futuros = sum(
            (
                f.monto_ars
                for f in analisis.flujos_proyectados
                if f.rol == "inversor" and f.monto_ars > ZERO
            ),
            ZERO,
        )
        pagos_futuros = sum(
            (
                -f.monto_ars
                for f in analisis.flujos_proyectados
                if f.rol == "deudor" and f.monto_ars < ZERO
            ),
            ZERO,
        )

        return PosicionFinancieraPersona(
            persona_id=persona_id,
            fecha_corte=corte,
            capital_invertido=money(analisis.resumen.capital_aportado_activo),
            capital_deuda_pendiente=money(analisis.resumen.capital_deudor_pendiente),
            posicion_neta_capital=money(analisis.resumen.posicion_neta_capital),
            cobros_reales=money(cobros_reales),
            pagos_reales=money(pagos_reales),
            flujo_neto_real=money(cobros_reales - pagos_reales),
            cobros_futuros_estimados=money(cobros_futuros),
            pagos_futuros_estimados=money(pagos_futuros),
            flujo_neto_futuro_estimado=money(cobros_futuros - pagos_futuros),
            movimientos_mensuales=_movimientos_mensuales(
                analisis.flujos_reales,
                corte,
                meses_historicos,
            ),
        )


class ServicioPosicionFinancieraPersona:
    """Caso de uso de lectura para la posición consolidada."""

    def __init__(self, db: BaseDatos) -> None:
        self._query = PosicionFinancieraPersonaQuery(db)

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        meses_historicos: int = 12,
    ) -> PosicionFinancieraPersona:
        return self._query.obtener(
            persona_id,
            fecha_corte=fecha_corte,
            meses_historicos=meses_historicos,
        )


def _primer_dia_mes(fecha: date) -> date:
    return date(fecha.year, fecha.month, 1)


def _retroceder_meses(fecha: date, cantidad: int) -> date:
    indice = fecha.year * 12 + fecha.month - 1 - cantidad
    return date(indice // 12, indice % 12 + 1, 1)


def _movimientos_mensuales(
    flujos: tuple[FlujoCajaFinanciero, ...],
    corte: date,
    meses_historicos: int,
) -> tuple[MovimientoMensualReal, ...]:
    inicio = _retroceder_meses(_primer_dia_mes(corte), meses_historicos - 1)
    acumulado = ZERO
    resultado: list[MovimientoMensualReal] = []

    for offset in range(meses_historicos):
        periodo = _retroceder_meses(
            _primer_dia_mes(corte),
            meses_historicos - 1 - offset,
        )
        siguiente = (
            date(periodo.year + 1, 1, 1)
            if periodo.month == 12
            else date(periodo.year, periodo.month + 1, 1)
        )

        del_mes = [
            flujo
            for flujo in flujos
            if periodo <= flujo.fecha < siguiente
        ]
        entradas = sum(
            (f.monto_ars for f in del_mes if f.monto_ars > ZERO),
            ZERO,
        )
        salidas = sum(
            (-f.monto_ars for f in del_mes if f.monto_ars < ZERO),
            ZERO,
        )
        neto = entradas - salidas
        acumulado += neto

        resultado.append(
            MovimientoMensualReal(
                periodo=periodo,
                entradas=entradas,
                salidas=salidas,
                neto=money(neto),
                acumulado=money(acumulado),
            )
        )

    return tuple(resultado)
