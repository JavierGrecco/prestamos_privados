from datetime import date
from decimal import Decimal

import pytest

from dominio.devengamiento_v3 import PoliticaInteres
from dominio.excepciones import ErrorInvariante, ErrorValidacion
from dominio.exposicion_capital_v3 import PuntoCapitalProgramado
from dominio.motor_pagos_v3 import AplicacionPago, OrigenImputacion
from dominio.trayectoria_capital_v3 import (
    EventoReduccionCapital,
    calcular_exposicion_desde_eventos_capital,
    construir_trayectoria_capital_real,
    eventos_capital_desde_plan,
)
from dominio.tipos import ConceptoImputacion, ConvencionDias, ModalidadTasa


def politica():
    return PoliticaInteres(
        tasa_anual=Decimal("0.30"),
        modalidad_tasa=ModalidadTasa.TNA,
        convencion_dias=ConvencionDias.ACTUAL_365,
    )


def evento(fecha, monto, ref=None, origen=OrigenImputacion.SALDO_CONTRACTUAL):
    return EventoReduccionCapital(
        fecha_valor=fecha,
        monto=Decimal(str(monto)),
        origen=origen,
        referencia=ref,
    )


def test_sin_eventos_conserva_capital():
    r = construir_trayectoria_capital_real(
        capital_inicial=Decimal("100000"),
        fecha_inicio_contrato=date(2026, 1, 1),
        fecha_desde=date(2026, 2, 1),
        fecha_hasta=date(2026, 3, 1),
        eventos=(),
    )
    assert r.puntos[0].capital == Decimal("100000.00")
    assert r.capital_al_final == Decimal("100000.00")


def test_evento_anterior_al_periodo_se_traslada_al_punto_inicial():
    r = construir_trayectoria_capital_real(
        capital_inicial=Decimal("100000"),
        fecha_inicio_contrato=date(2026, 1, 1),
        fecha_desde=date(2026, 2, 1),
        fecha_hasta=date(2026, 3, 1),
        eventos=(evento(date(2026, 1, 20), "10000", "PAGO_1"),),
    )
    assert r.capital_al_inicio == Decimal("90000.00")
    assert r.reducciones_antes_del_periodo == Decimal("10000.00")
    assert len(r.puntos) == 1


def test_evento_en_fecha_desde_es_efectivo_desde_el_inicio():
    r = construir_trayectoria_capital_real(
        capital_inicial=Decimal("100000"),
        fecha_inicio_contrato=date(2026, 1, 1),
        fecha_desde=date(2026, 2, 1),
        fecha_hasta=date(2026, 3, 1),
        eventos=(evento(date(2026, 2, 1), "10000", "PAGO_1"),),
    )
    assert r.capital_al_inicio == Decimal("90000.00")
    assert r.reducciones_en_el_periodo == Decimal("0.00")
    assert len(r.puntos) == 1


def test_evento_en_fecha_hasta_queda_fuera_del_intervalo():
    r = construir_trayectoria_capital_real(
        capital_inicial=Decimal("100000"),
        fecha_inicio_contrato=date(2026, 1, 1),
        fecha_desde=date(2026, 2, 1),
        fecha_hasta=date(2026, 3, 1),
        eventos=(evento(date(2026, 3, 1), "10000", "PAGO_1"),),
    )
    assert r.capital_al_inicio == Decimal("100000.00")
    assert r.reducciones_en_el_periodo == Decimal("0.00")
    assert len(r.puntos) == 1


def test_pago_intermedio_reduce_capital_desde_su_fecha():
    r = construir_trayectoria_capital_real(
        capital_inicial=Decimal("100000"),
        fecha_inicio_contrato=date(2026, 1, 1),
        fecha_desde=date(2026, 2, 1),
        fecha_hasta=date(2026, 3, 1),
        eventos=(evento(date(2026, 2, 15), "6000", "PAGO_1"),),
    )
    assert tuple((p.fecha, p.capital) for p in r.puntos) == (
        (date(2026, 2, 1), Decimal("100000.00")),
        (date(2026, 2, 15), Decimal("94000.00")),
    )
    assert r.reducciones_en_el_periodo == Decimal("6000.00")


def test_dos_reducciones_misma_fecha_se_conservan_y_acumulan():
    r = construir_trayectoria_capital_real(
        capital_inicial=Decimal("100000"),
        fecha_inicio_contrato=date(2026, 1, 1),
        fecha_desde=date(2026, 2, 1),
        fecha_hasta=date(2026, 3, 1),
        eventos=(
            evento(date(2026, 2, 15), "4000", "PAGO_A"),
            evento(date(2026, 2, 15), "6000", "PAGO_B"),
        ),
    )
    assert r.puntos[-1].capital == Decimal("90000.00")
    assert r.reducciones_en_el_periodo == Decimal("10000.00")
    assert r.puntos[-1].referencia == "PAGO_A|PAGO_B"


def test_rechaza_reduccion_superior_al_capital():
    with pytest.raises(ErrorInvariante):
        construir_trayectoria_capital_real(
            capital_inicial=Decimal("10000"),
            fecha_inicio_contrato=date(2026, 1, 1),
            fecha_desde=date(2026, 2, 1),
            fecha_hasta=date(2026, 3, 1),
            eventos=(evento(date(2026, 2, 10), "10001", "PAGO_1"),),
        )


def test_rechaza_evento_anterior_al_inicio_del_contrato():
    with pytest.raises(ErrorValidacion):
        construir_trayectoria_capital_real(
            capital_inicial=Decimal("10000"),
            fecha_inicio_contrato=date(2026, 2, 1),
            fecha_desde=date(2026, 2, 10),
            fecha_hasta=date(2026, 3, 1),
            eventos=(evento(date(2026, 1, 31), "100", "INVALIDO"),),
        )


def test_rechaza_fecha_desde_anterior_al_contrato():
    with pytest.raises(ErrorValidacion):
        construir_trayectoria_capital_real(
            capital_inicial=Decimal("10000"),
            fecha_inicio_contrato=date(2026, 2, 1),
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 3, 1),
            eventos=(),
        )


def test_rechaza_eventos_duplicados_misma_fecha_y_referencia():
    with pytest.raises(ErrorValidacion):
        construir_trayectoria_capital_real(
            capital_inicial=Decimal("10000"),
            fecha_inicio_contrato=date(2026, 1, 1),
            fecha_desde=date(2026, 2, 1),
            fecha_hasta=date(2026, 3, 1),
            eventos=(
                evento(date(2026, 2, 10), "100", "PAGO_X"),
                evento(date(2026, 2, 10), "200", "PAGO_X"),
            ),
        )


def test_extrae_solo_aplicaciones_de_capital_de_plan():
    class PlanFalso:
        prestamo_id = 77
        fecha_valor = date(2026, 2, 15)
        aplicaciones = (
            AplicacionPago(
                cuota_id=1,
                concepto=ConceptoImputacion.INTERES,
                monto=Decimal("300"),
                origen=OrigenImputacion.SALDO_CONTRACTUAL,
            ),
            AplicacionPago(
                cuota_id=1,
                concepto=ConceptoImputacion.CAPITAL,
                monto=Decimal("700"),
                origen=OrigenImputacion.SALDO_CONTRACTUAL,
            ),
        )

    eventos = eventos_capital_desde_plan(PlanFalso(), referencia_pago="PAGO_99")
    assert len(eventos) == 1
    assert eventos[0].monto == Decimal("700.00")
    assert eventos[0].fecha_valor == date(2026, 2, 15)
    assert eventos[0].referencia == "PAGO_99:CUOTA_1"


def test_plan_sin_capital_no_genera_eventos():
    class PlanFalso:
        prestamo_id = 77
        fecha_valor = date(2026, 2, 15)
        aplicaciones = (
            AplicacionPago(
                cuota_id=1,
                concepto=ConceptoImputacion.INTERES,
                monto=Decimal("700"),
                origen=OrigenImputacion.SALDO_CONTRACTUAL,
            ),
        )

    assert eventos_capital_desde_plan(PlanFalso()) == ()


def test_puente_v3d_v3c_calcula_exposicion_por_tramos():
    programado = (
        PuntoCapitalProgramado(date(2026, 1, 1), Decimal("100000"), "INICIO"),
        PuntoCapitalProgramado(date(2026, 2, 1), Decimal("90000"), "CUOTA_1_POST"),
    )
    trayectoria, exposicion = calcular_exposicion_desde_eventos_capital(
        capital_inicial=Decimal("100000"),
        fecha_inicio_contrato=date(2026, 1, 1),
        fecha_desde=date(2026, 2, 1),
        fecha_hasta=date(2026, 3, 1),
        eventos_capital=(evento(date(2026, 2, 15), "6000", "PAGO_1"),),
        capital_programado=programado,
        politica_interes=politica(),
    )
    assert trayectoria.puntos[-1].capital == Decimal("94000.00")
    assert [t.exceso_capital for t in exposicion.tramos] == [
        Decimal("10000.00"),
        Decimal("4000.00"),
    ]
    assert exposicion.interes_adicional_total == Decimal("161.10")


def test_trayectoria_es_determinista_independientemente_del_orden_de_entrada():
    eventos = (
        evento(date(2026, 2, 15), "6000", "PAGO_B"),
        evento(date(2026, 2, 10), "2000", "PAGO_A"),
    )
    r1 = construir_trayectoria_capital_real(
        capital_inicial=Decimal("100000"),
        fecha_inicio_contrato=date(2026, 1, 1),
        fecha_desde=date(2026, 2, 1),
        fecha_hasta=date(2026, 3, 1),
        eventos=eventos,
    )
    r2 = construir_trayectoria_capital_real(
        capital_inicial=Decimal("100000"),
        fecha_inicio_contrato=date(2026, 1, 1),
        fecha_desde=date(2026, 2, 1),
        fecha_hasta=date(2026, 3, 1),
        eventos=tuple(reversed(eventos)),
    )
    assert r1 == r2
