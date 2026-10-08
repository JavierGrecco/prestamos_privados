"""Read model de escenarios macroeconómicos sobre la planificación personal.

El contrato y los flujos nominales permanecen iguales. Un escenario solamente
traduce esos mismos flujos a valor real y, cuando hay tipo de cambio de
referencia, a una referencia USD.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aplicacion.consultas.analisis_financiero import (
    AnalisisFinancieroQuery,
    FlujoCajaFinanciero,
)
from dominio.escenarios import (
    EscenarioMacro,
    factor_acumulado_mensual,
    escenarios_predefinidos_argentina,
)
from dominio.licuacion import valor_real
from dominio.tipos import money
from infraestructura.db import BaseDatos
from infraestructura.repositorios import PersonaRepo

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class ResultadoEscenarioPersona:
    """Impacto agregado de un escenario sobre los flujos futuros."""

    nombre: str
    descripcion: str
    inflacion_mensual: Decimal
    devaluacion_mensual: Decimal
    cobros_nominales: Decimal
    pagos_nominales: Decimal
    neto_nominal: Decimal
    cobros_reales: Decimal
    pagos_reales: Decimal
    neto_real: Decimal
    cobros_usd: Decimal | None
    pagos_usd: Decimal | None
    neto_usd: Decimal | None


@dataclass(frozen=True)
class ResultadoEscenariosPersona:
    """Comparación completa para una persona."""

    persona_id: int
    fecha_corte: date
    horizonte_meses: int
    tipo_cambio_inicial: Decimal | None
    resultados: tuple[ResultadoEscenarioPersona, ...]
    flujos_proyectados: tuple[FlujoCajaFinanciero, ...]


class EscenariosPersonaQuery:
    """Aplica escenarios a los flujos proyectados ya calculados."""

    def __init__(self, db: BaseDatos) -> None:
        self._personas = PersonaRepo(db)
        self._analisis = AnalisisFinancieroQuery(db)

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        horizonte_meses: int = 12,
        tipo_cambio_inicial: Decimal | None = None,
        escenarios: tuple[EscenarioMacro, ...] | None = None,
    ) -> ResultadoEscenariosPersona:
        if persona_id <= 0:
            raise ValueError("persona_id debe ser positivo")
        if horizonte_meses < 1 or horizonte_meses > 60:
            raise ValueError("horizonte_meses debe estar entre 1 y 60")

        persona = self._personas.obtener(persona_id)
        if persona is None:
            raise ValueError(f"La persona {persona_id} no existe")

        corte = fecha_corte or date.today()
        escenarios = escenarios or tuple(escenarios_predefinidos_argentina())

        tc = None
        if tipo_cambio_inicial is not None:
            tc = Decimal(str(tipo_cambio_inicial))
            if tc <= ZERO:
                raise ValueError("El tipo de cambio inicial debe ser mayor a cero")
        else:
            tc = _ultimo_tipo_cambio_conocido(
                self._analisis.obtener(persona_id, fecha_corte=corte).flujos_reales
            )

        analisis = self._analisis.obtener(persona_id, fecha_corte=corte)
        fin = _fin_horizonte(corte, horizonte_meses)
        flujos = tuple(
            flujo
            for flujo in analisis.flujos_proyectados
            if corte < flujo.fecha <= fin
        )

        resultados = tuple(
            _evaluar_escenario(
                escenario,
                flujos,
                corte,
                tc,
            )
            for escenario in escenarios
        )

        return ResultadoEscenariosPersona(
            persona_id=persona_id,
            fecha_corte=corte,
            horizonte_meses=horizonte_meses,
            tipo_cambio_inicial=tc,
            resultados=resultados,
            flujos_proyectados=flujos,
        )


class ServicioEscenariosPersona:
    """Caso de uso de lectura para comparar escenarios."""

    def __init__(self, db: BaseDatos) -> None:
        self._query = EscenariosPersonaQuery(db)

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        horizonte_meses: int = 12,
        tipo_cambio_inicial: Decimal | None = None,
        escenarios: tuple[EscenarioMacro, ...] | None = None,
    ) -> ResultadoEscenariosPersona:
        return self._query.obtener(
            persona_id,
            fecha_corte=fecha_corte,
            horizonte_meses=horizonte_meses,
            tipo_cambio_inicial=tipo_cambio_inicial,
            escenarios=escenarios,
        )


def _fin_horizonte(corte: date, horizonte_meses: int) -> date:
    from datetime import timedelta

    primer_mes = date(corte.year, corte.month, 1)
    siguiente = _sumar_meses(primer_mes, horizonte_meses + 1)
    return siguiente - timedelta(days=1)


def _sumar_meses(fecha: date, cantidad: int) -> date:
    indice = fecha.year * 12 + fecha.month - 1 + cantidad
    return date(indice // 12, indice % 12 + 1, 1)


def _mes_escenario(corte: date, fecha: date) -> int:
    diferencia = (
        (fecha.year - corte.year) * 12
        + fecha.month
        - corte.month
    )
    return max(1, diferencia)


def _ultimo_tipo_cambio_conocido(
    flujos: tuple[FlujoCajaFinanciero, ...],
) -> Decimal | None:
    disponibles = [
        flujo
        for flujo in flujos
        if flujo.tc_ars_usd is not None and flujo.tc_ars_usd > ZERO
    ]
    if not disponibles:
        return None
    ultimo = max(disponibles, key=lambda flujo: flujo.fecha)
    return Decimal(str(ultimo.tc_ars_usd))


def _evaluar_escenario(
    escenario: EscenarioMacro,
    flujos: tuple[FlujoCajaFinanciero, ...],
    corte: date,
    tipo_cambio_inicial: Decimal | None,
) -> ResultadoEscenarioPersona:
    cobros_nominales = money(
        sum(
            (
                flujo.monto_ars
                for flujo in flujos
                if flujo.rol == "inversor" and flujo.monto_ars > ZERO
            ),
            ZERO,
        )
    )
    pagos_nominales = money(
        sum(
            (
                -flujo.monto_ars
                for flujo in flujos
                if flujo.rol == "deudor" and flujo.monto_ars < ZERO
            ),
            ZERO,
        )
    )

    cobros_reales = ZERO
    pagos_reales = ZERO
    cobros_usd = ZERO if tipo_cambio_inicial else None
    pagos_usd = ZERO if tipo_cambio_inicial else None

    for flujo in flujos:
        meses = _mes_escenario(corte, flujo.fecha)
        monto = abs(flujo.monto_ars)
        real = valor_real(
            monto,
            escenario.inflacion_mensual,
            meses,
        )

        if flujo.rol == "inversor" and flujo.monto_ars > ZERO:
            cobros_reales += real
        elif flujo.rol == "deudor" and flujo.monto_ars < ZERO:
            pagos_reales += real

        if tipo_cambio_inicial is not None:
            factor_tc = factor_acumulado_mensual(
                escenario.devaluacion_mensual,
                meses,
            )
            usd = money(monto / (tipo_cambio_inicial * factor_tc))
            if flujo.rol == "inversor" and flujo.monto_ars > ZERO:
                cobros_usd += usd
            elif flujo.rol == "deudor" and flujo.monto_ars < ZERO:
                pagos_usd += usd

    cobros_reales = money(cobros_reales)
    pagos_reales = money(pagos_reales)

    return ResultadoEscenarioPersona(
        nombre=escenario.nombre,
        descripcion=escenario.descripcion,
        inflacion_mensual=escenario.inflacion_mensual,
        devaluacion_mensual=escenario.devaluacion_mensual,
        cobros_nominales=cobros_nominales,
        pagos_nominales=pagos_nominales,
        neto_nominal=money(cobros_nominales - pagos_nominales),
        cobros_reales=cobros_reales,
        pagos_reales=pagos_reales,
        neto_real=money(cobros_reales - pagos_reales),
        cobros_usd=(
            money(cobros_usd) if cobros_usd is not None else None
        ),
        pagos_usd=(
            money(pagos_usd) if pagos_usd is not None else None
        ),
        neto_usd=(
            money(cobros_usd - pagos_usd)
            if cobros_usd is not None and pagos_usd is not None
            else None
        ),
    )
