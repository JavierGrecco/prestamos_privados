from datetime import date
from decimal import Decimal

import pytest

from dominio.devengamiento_v3 import PoliticaInteres
from dominio.excepciones import ErrorInvariante, ErrorValidacion
from dominio.exposicion_capital_v3 import (
    PuntoCapitalProgramado,
    PuntoCapitalReal,
    calcular_exposicion_capital,
    puntos_programados_desde_tabla,
)
from dominio.tipos import ConvencionDias, ModalidadTasa


def politica():
    return PoliticaInteres(
        tasa_anual=Decimal("0.30"),
        modalidad_tasa=ModalidadTasa.TNA,
        convencion_dias=ConvencionDias.ACTUAL_365,
    )


def pprog(fecha, capital, ref=None):
    return PuntoCapitalProgramado(fecha, Decimal(str(capital)), ref)


def preal(fecha, capital, ref=None):
    return PuntoCapitalReal(fecha, Decimal(str(capital)), ref)


def test_sin_exceso_no_genera_interes():
    resultado = calcular_exposicion_capital(
        fecha_desde=date(2026, 9, 1),
        fecha_hasta=date(2026, 10, 1),
        capital_programado=(pprog(date(2026, 1, 1), "100000"),),
        capital_real=(preal(date(2026, 1, 1), "100000"),),
        politica=politica(),
    )
    assert resultado.interes_adicional_total == Decimal("0.00")
    assert resultado.tramos[0].exceso_capital == Decimal("0.00")
    assert resultado.tramos[0].devengamiento is None


def test_exceso_constante_genera_interes_solo_sobre_el_exceso():
    resultado = calcular_exposicion_capital(
        fecha_desde=date(2026, 9, 1),
        fecha_hasta=date(2026, 10, 1),
        capital_programado=(pprog(date(2026, 1, 1), "100000"),),
        capital_real=(preal(date(2026, 1, 1), "120000"),),
        politica=politica(),
    )
    tramo = resultado.tramos[0]
    assert tramo.exceso_capital == Decimal("20000.00")
    assert tramo.devengamiento is not None
    assert tramo.devengamiento.base == Decimal("20000.00")
    assert resultado.interes_adicional_total == Decimal("493.15")


def test_pago_intermedio_reduce_la_exposicion_desde_su_fecha():
    resultado = calcular_exposicion_capital(
        fecha_desde=date(2026, 9, 1),
        fecha_hasta=date(2026, 10, 1),
        capital_programado=(pprog(date(2026, 1, 1), "100000"),),
        capital_real=(
            preal(date(2026, 1, 1), "120000", "ESTADO_INICIAL"),
            preal(date(2026, 9, 16), "110000", "PAGO_1"),
        ),
        politica=politica(),
    )
    assert len(resultado.tramos) == 2
    assert resultado.tramos[0].exceso_capital == Decimal("20000.00")
    assert resultado.tramos[1].exceso_capital == Decimal("10000.00")
    assert resultado.interes_adicional_total == Decimal("369.87")


def test_cambio_del_cronograma_divide_el_tramo():
    resultado = calcular_exposicion_capital(
        fecha_desde=date(2026, 9, 1),
        fecha_hasta=date(2026, 10, 15),
        capital_programado=(
            pprog(date(2026, 1, 1), "100000", "INICIO"),
            pprog(date(2026, 10, 1), "90000", "CUOTA_1_POST"),
        ),
        capital_real=(preal(date(2026, 1, 1), "120000"),),
        politica=politica(),
    )
    assert [t.fecha_desde for t in resultado.tramos] == [
        date(2026, 9, 1),
        date(2026, 10, 1),
    ]
    assert [t.exceso_capital for t in resultado.tramos] == [
        Decimal("20000.00"),
        Decimal("30000.00"),
    ]


def test_si_real_es_menor_que_programado_no_se_cobra_interes_adicional():
    resultado = calcular_exposicion_capital(
        fecha_desde=date(2026, 9, 1),
        fecha_hasta=date(2026, 10, 1),
        capital_programado=(pprog(date(2026, 1, 1), "100000"),),
        capital_real=(preal(date(2026, 1, 1), "90000"),),
        politica=politica(),
    )
    assert resultado.tramos[0].exceso_capital == Decimal("-10000.00")
    assert resultado.interes_adicional_total == Decimal("0.00")


def test_rechaza_serie_sin_punto_vigente_al_inicio():
    with pytest.raises(ErrorValidacion):
        calcular_exposicion_capital(
            fecha_desde=date(2026, 9, 1),
            fecha_hasta=date(2026, 10, 1),
            capital_programado=(pprog(date(2026, 9, 5), "100000"),),
            capital_real=(preal(date(2026, 1, 1), "120000"),),
            politica=politica(),
        )


def test_rechaza_puntos_duplicados_en_una_serie():
    with pytest.raises(ErrorValidacion):
        calcular_exposicion_capital(
            fecha_desde=date(2026, 9, 1),
            fecha_hasta=date(2026, 10, 1),
            capital_programado=(
                pprog(date(2026, 1, 1), "100000"),
                pprog(date(2026, 1, 1), "90000"),
            ),
            capital_real=(preal(date(2026, 1, 1), "120000"),),
            politica=politica(),
        )


def test_adapter_de_tabla_de_amortizacion():
    puntos = puntos_programados_desde_tabla(
        fecha_inicio=date(2026, 1, 1),
        capital_inicial=Decimal("100000"),
        tabla=(
            {"numero": 1, "vencimiento": date(2026, 2, 1), "saldo": Decimal("95000")},
            {"numero": 2, "vencimiento": date(2026, 3, 1), "saldo": Decimal("89000")},
        ),
    )
    assert tuple((p.fecha, p.capital) for p in puntos) == (
        (date(2026, 1, 1), Decimal("100000.00")),
        (date(2026, 2, 1), Decimal("95000.00")),
        (date(2026, 3, 1), Decimal("89000.00")),
    )


def test_resultado_valida_contiguedad_y_limites():
    resultado = calcular_exposicion_capital(
        fecha_desde=date(2026, 9, 1),
        fecha_hasta=date(2026, 10, 1),
        capital_programado=(pprog(date(2026, 1, 1), "100000"),),
        capital_real=(preal(date(2026, 1, 1), "120000"),),
        politica=politica(),
    )
    resultado.validar()
    assert resultado.exposicion_maxima == Decimal("20000.00")


def test_periodo_cero_devuelve_resultado_vacio():
    fecha = date(2026, 9, 1)
    resultado = calcular_exposicion_capital(
        fecha_desde=fecha,
        fecha_hasta=fecha,
        capital_programado=(pprog(fecha, "100000"),),
        capital_real=(preal(fecha, "120000"),),
        politica=politica(),
    )
    assert resultado.tramos == ()
    assert resultado.interes_adicional_total == Decimal("0.00")


def test_exposicion_es_determinista():
    kwargs = dict(
        fecha_desde=date(2026, 9, 1),
        fecha_hasta=date(2026, 10, 1),
        capital_programado=(pprog(date(2026, 1, 1), "100000"),),
        capital_real=(preal(date(2026, 1, 1), "120000"),),
        politica=politica(),
    )
    assert calcular_exposicion_capital(**kwargs) == calcular_exposicion_capital(**kwargs)
