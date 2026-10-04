"""
Simulador de escenarios macroeconómicos.

Responde a la pregunta: ¿qué pasa con mi préstamo si la inflación
o el tipo de cambio se comportan de distintas maneras?

No predice el futuro. Toma los flujos calculados por el motor de
amortización y los ajusta por distintos escenarios para que el
usuario pueda ver el impacto.

Concepto clave: la deuda contractual en ARS no cambia. Lo que cambia
es el VALOR ECONÓMICO de los flujos, medido en términos reales
(ajustados por inflación) y en dólares.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from .tipos import money, SistemaAmortizacion, ModalidadTasa
from .amortizacion import generar_tabla


@dataclass
class EscenarioMacro:
    """
    Un escenario macroeconómico.

    Atributos:
        nombre: cómo llamarlo ("Base", "Optimista", etc.)
        inflacion_mensual: inflación promedio mensual esperada.
            0.05 = 5% mensual.
        devaluacion_mensual: devaluación promedio mensual esperada
            del peso frente al dólar. 0.08 = 8% mensual.
        descripcion: texto libre para documentar el escenario.
    """
    nombre: str
    inflacion_mensual: Decimal
    devaluacion_mensual: Decimal
    descripcion: str = ""


@dataclass
class ResultadoEscenario:
    """Resultado del análisis de un escenario sobre un préstamo."""
    escenario: EscenarioMacro
    flujos_nominales: list[dict]
    flujos_reales: list[dict]
    flujos_usd: list[dict]
    cuota_final_real: Decimal
    cuota_final_usd: Decimal
    perdida_poder_compra_pct: Decimal


def _factor_acumulado(tasa_mensual: Decimal, meses: int) -> Decimal:
    """
    Factor de acumulación compuesta.

    Con 5% mensual durante 12 meses, el factor es (1.05)^12 ≈ 1.796,
    o sea que los precios casi se duplicaron.
    """
    return (Decimal("1") + tasa_mensual) ** meses


def simular_escenario(
    capital: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    meses: int,
    fecha_inicio: date,
    escenario: EscenarioMacro,
    sistema: SistemaAmortizacion = SistemaAmortizacion.FRANCES,
    tc_inicial: Decimal | None = None,
) -> ResultadoEscenario:
    """
    Simula el préstamo bajo un escenario macroeconómico.

    Devuelve un ResultadoEscenario con los flujos en tres monedas:
    nominal, real (ajustado por inflación) y USD.
    """
    tabla = generar_tabla(
        capital=capital,
        tasa_anual=tasa_anual,
        modalidad=modalidad,
        meses=meses,
        fecha_inicio=fecha_inicio,
        sistema=sistema,
    )

    inflacion = escenario.inflacion_mensual
    devaluacion = escenario.devaluacion_mensual

    flujos_nominales: list[dict] = []
    flujos_reales: list[dict] = []
    flujos_usd: list[dict] = []

    for i, fila in enumerate(tabla):
        mes = i + 1
        factor_infl = _factor_acumulado(inflacion, mes)
        factor_deval = _factor_acumulado(devaluacion, mes)

        cuota_nom = fila["cuota"]
        cuota_real = money(cuota_nom / factor_infl)
        if tc_inicial:
            tc_mes = tc_inicial * factor_deval
            cuota_usd = money(cuota_nom / tc_mes)
        else:
            cuota_usd = money(cuota_nom / factor_deval)

        flujos_nominales.append({
            "mes": mes,
            "cuota": cuota_nom,
            "interes": fila["interes"],
            "capital": fila["capital"],
        })
        flujos_reales.append({
            "mes": mes,
            "cuota": cuota_real,
            "interes": money(fila["interes"] / factor_infl),
            "capital": money(fila["capital"] / factor_infl),
        })
        flujos_usd.append({
            "mes": mes,
            "cuota": cuota_usd,
            "interes": money(fila["interes"] / factor_deval) if tc_inicial is None
                       else money(fila["interes"] / (tc_inicial * factor_deval)),
            "capital": money(fila["capital"] / factor_deval) if tc_inicial is None
                       else money(fila["capital"] / (tc_inicial * factor_deval)),
        })

    cuota_final_nom = tabla[-1]["cuota"]
    factor_infl_final = _factor_acumulado(inflacion, meses)
    factor_deval_final = _factor_acumulado(devaluacion, meses)
    cuota_final_real = money(cuota_final_nom / factor_infl_final)
    if tc_inicial:
        cuota_final_usd = money(cuota_final_nom / (tc_inicial * factor_deval_final))
    else:
        cuota_final_usd = money(cuota_final_nom / factor_deval_final)

    cuota_primera = tabla[0]["cuota"]
    perdida_pct = money(
        (Decimal("1") - (cuota_final_real / cuota_primera)) * Decimal("100")
    )

    return ResultadoEscenario(
        escenario=escenario,
        flujos_nominales=flujos_nominales,
        flujos_reales=flujos_reales,
        flujos_usd=flujos_usd,
        cuota_final_real=cuota_final_real,
        cuota_final_usd=cuota_final_usd,
        perdida_poder_compra_pct=perdida_pct,
    )


def comparar_escenarios(
    capital: Decimal,
    tasa_anual: Decimal,
    modalidad: ModalidadTasa,
    meses: int,
    fecha_inicio: date,
    escenarios: Iterable[EscenarioMacro],
    sistema: SistemaAmortizacion = SistemaAmortizacion.FRANCES,
    tc_inicial: Decimal | None = None,
) -> list[ResultadoEscenario]:
    """Corre el simulador para varios escenarios."""
    return [
        simular_escenario(
            capital=capital,
            tasa_anual=tasa_anual,
            modalidad=modalidad,
            meses=meses,
            fecha_inicio=fecha_inicio,
            escenario=esc,
            sistema=sistema,
            tc_inicial=tc_inicial,
        )
        for esc in escenarios
    ]


def escenarios_predefinidos_argentina() -> list[EscenarioMacro]:
    """
    Escenarios típicos para el contexto argentino.

    No son predicciones. Son referencias razonables para comparar.
    El usuario siempre puede definir los suyos.
    """
    return [
        EscenarioMacro(
            nombre="Optimista",
            inflacion_mensual=Decimal("0.03"),
            devaluacion_mensual=Decimal("0.04"),
            descripcion="Inflación y devaluación moderadas, estabilización.",
        ),
        EscenarioMacro(
            nombre="Base",
            inflacion_mensual=Decimal("0.05"),
            devaluacion_mensual=Decimal("0.07"),
            descripcion="Escenario central de referencia para planificación.",
        ),
        EscenarioMacro(
            nombre="Pesimista",
            inflacion_mensual=Decimal("0.08"),
            devaluacion_mensual=Decimal("0.12"),
            descripcion="Inflación alta y devaluación acelerada.",
        ),
        EscenarioMacro(
            nombre="Crisis",
            inflacion_mensual=Decimal("0.15"),
            devaluacion_mensual=Decimal("0.25"),
            descripcion="Escenario extremo para stress testing.",
        ),
    ]