"""Pruebas del generador de amortización con calendario explícito."""
from datetime import date
from decimal import Decimal, localcontext

import pytest
from dateutil.relativedelta import relativedelta

from dominio import (
    ConvencionDias,
    ErrorValidacion,
    ModalidadTasa,
    SistemaAmortizacion,
    generar_tabla,
    generar_tabla_por_fechas,
    money,
    rate,
)


CAPITAL = Decimal("1000000")
TASA = Decimal("0.30")


def _fechas_mensuales(inicio: date, cantidad: int) -> list[date]:
    return [inicio + relativedelta(months=n) for n in range(1, cantidad + 1)]


@pytest.mark.parametrize("sistema", [SistemaAmortizacion.FRANCES, SistemaAmortizacion.ALEMAN])
@pytest.mark.parametrize("modalidad", [ModalidadTasa.TNA, ModalidadTasa.TEA])
def test_convencion_mensual_reproduce_exactamente_el_motor_legacy(sistema, modalidad):
    inicio = date(2026, 1, 31)
    fechas = _fechas_mensuales(inicio, 24)
    legado = generar_tabla(
        capital=CAPITAL,
        tasa_anual=TASA,
        modalidad=modalidad,
        meses=24,
        fecha_inicio=inicio,
        sistema=sistema,
    )
    nuevo = generar_tabla_por_fechas(
        capital=CAPITAL,
        tasa_anual=TASA,
        modalidad=modalidad,
        sistema=sistema,
        fecha_inicio_periodo=inicio,
        fechas_vencimiento=fechas,
        convencion=ConvencionDias.MENSUAL,
    )

    assert nuevo == legado


def test_actual_365_tna_calcula_el_primer_periodo_con_dias_reales():
    tabla = generar_tabla_por_fechas(
        capital=Decimal("100000"),
        tasa_anual=Decimal("0.365"),
        modalidad=ModalidadTasa.TNA,
        sistema=SistemaAmortizacion.ALEMAN,
        fecha_inicio_periodo=date(2026, 1, 1),
        fechas_vencimiento=[date(2026, 2, 1), date(2026, 3, 1)],
        convencion=ConvencionDias.ACTUAL_365,
    )

    # 31 días: 100000 * 36.5% * 31/365 = 3100.
    assert tabla[0]["interes"] == Decimal("3100.00")
    # 28 días, sobre 50000 de capital restante.
    assert tabla[1]["interes"] == Decimal("1400.00")
    assert tabla[-1]["saldo"] == Decimal("0.00")


def test_tea_actual_365_usa_factor_compuesto_sobre_la_fraccion_del_anio():
    tabla = generar_tabla_por_fechas(
        capital=Decimal("100000"),
        tasa_anual=Decimal("0.21"),
        modalidad=ModalidadTasa.TEA,
        sistema=SistemaAmortizacion.ALEMAN,
        fecha_inicio_periodo=date(2026, 1, 1),
        fechas_vencimiento=[date(2026, 2, 1)],
        convencion=ConvencionDias.ACTUAL_365,
    )
    with localcontext() as contexto:
        contexto.prec = 40
        factor = contexto.power(Decimal("1.21"), Decimal(31) / Decimal(365)) - Decimal("1")
    assert tabla[0]["interes"] == money(Decimal("100000") * rate(factor))


def test_30e_360_trata_fin_de_mes_de_manera_determinista():
    tabla = generar_tabla_por_fechas(
        capital=Decimal("100000"),
        tasa_anual=Decimal("0.36"),
        modalidad=ModalidadTasa.TNA,
        sistema=SistemaAmortizacion.ALEMAN,
        fecha_inicio_periodo=date(2026, 1, 31),
        fechas_vencimiento=[date(2026, 2, 28), date(2026, 3, 31)],
        convencion=ConvencionDias.TREINTA_360,
    )

    assert tabla[0]["interes"] == Decimal("3000.00")
    assert tabla[1]["interes"] == Decimal("1500.00")
    assert tabla[-1]["saldo"] == Decimal("0.00")


def test_actual_actual_separa_periodo_que_cruza_anio_bisiesto():
    tabla = generar_tabla_por_fechas(
        capital=Decimal("100000"),
        tasa_anual=Decimal("0.366"),
        modalidad=ModalidadTasa.TNA,
        sistema=SistemaAmortizacion.ALEMAN,
        fecha_inicio_periodo=date(2024, 12, 15),
        fechas_vencimiento=[date(2025, 1, 15)],
        convencion=ConvencionDias.ACTUAL_ACTUAL,
    )
    assert tabla[0]["interes"] == Decimal("3103.84")
    assert tabla[0]["saldo"] == Decimal("0.00")


def test_actual_360_es_independiente_de_actual_365():
    args = {
        "capital": Decimal("100000"),
        "tasa_anual": Decimal("0.36"),
        "modalidad": ModalidadTasa.TNA,
        "sistema": SistemaAmortizacion.ALEMAN,
        "fecha_inicio_periodo": date(2026, 1, 1),
        "fechas_vencimiento": [date(2026, 2, 1)],
    }
    actual_365 = generar_tabla_por_fechas(**args, convencion=ConvencionDias.ACTUAL_365)
    actual_360 = generar_tabla_por_fechas(**args, convencion=ConvencionDias.ACTUAL_360)

    assert actual_365[0]["interes"] == Decimal("3057.53")
    assert actual_360[0]["interes"] == Decimal("3100.00")
    assert actual_360[0]["interes"] > actual_365[0]["interes"]


def test_mensual_rechaza_primera_fecha_irregular_en_vez_de_asumir_interes():
    with pytest.raises(ErrorValidacion, match="aniversarios mensuales"):
        generar_tabla_por_fechas(
            capital=CAPITAL,
            tasa_anual=TASA,
            modalidad=ModalidadTasa.TNA,
            sistema=SistemaAmortizacion.FRANCES,
            fecha_inicio_periodo=date(2026, 1, 1),
            fechas_vencimiento=[date(2026, 2, 10), date(2026, 3, 1)],
            convencion=ConvencionDias.MENSUAL,
        )


@pytest.mark.parametrize(
    "fechas",
    [
        [],
        [date(2026, 1, 1)],
        [date(2026, 2, 1), date(2026, 2, 1)],
        [date(2026, 3, 1), date(2026, 2, 1)],
    ],
)
def test_rechaza_calendarios_vacios_no_ordenados_o_no_futuros(fechas):
    with pytest.raises(ErrorValidacion):
        generar_tabla_por_fechas(
            capital=CAPITAL,
            tasa_anual=TASA,
            modalidad=ModalidadTasa.TNA,
            sistema=SistemaAmortizacion.FRANCES,
            fecha_inicio_periodo=date(2026, 2, 1),
            fechas_vencimiento=fechas,
            convencion=ConvencionDias.ACTUAL_365,
        )


def test_interes_only_se_rechaza_hasta_integrar_su_regla_especializada():
    with pytest.raises(ErrorValidacion, match="INTERES_ONLY"):
        generar_tabla_por_fechas(
            capital=CAPITAL,
            tasa_anual=TASA,
            modalidad=ModalidadTasa.TNA,
            sistema=SistemaAmortizacion.INTERES_ONLY,
            fecha_inicio_periodo=date(2026, 1, 1),
            fechas_vencimiento=[date(2026, 2, 1)],
            convencion=ConvencionDias.ACTUAL_365,
        )
