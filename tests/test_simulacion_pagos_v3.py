from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest

from aplicacion.servicios.simulacion_pagos_v3 import (
    ContextoSimulacionV3,
    mapear_cuotas_a_snapshot_v3,
    simular_desde_cuotas_v3,
)
from dominio.excepciones import ErrorInvariante, ErrorValidacion


@dataclass
class CuotaFalsa:
    id: int
    numero: int
    vencimiento: date
    estado: str = "PENDIENTE"
    interes_pendiente: Decimal = Decimal("20000")
    capital_pendiente: Decimal = Decimal("100000")
    mora_pendiente: Decimal = Decimal("0")
    tuvo_pago_parcial: bool = False
    cuota: Decimal = Decimal("120000")


def cuota(n, cid=None, venc=None, estado="PENDIENTE", interes="20000", capital="100000", mora="0", parcial=False):
    return CuotaFalsa(
        id=cid or n,
        numero=n,
        vencimiento=venc or date(2026, 9, n),
        estado=estado,
        interes_pendiente=Decimal(interes),
        capital_pendiente=Decimal(capital),
        mora_pendiente=Decimal(mora),
        tuvo_pago_parcial=parcial,
    )


def test_contexto_normaliza_monto():
    c = ContextoSimulacionV3(10, date(2026, 9, 10), 0, Decimal("50000.007"))
    assert c.monto_recibido == Decimal("50000.01")


def test_contexto_rechaza_monto_no_positivo():
    with pytest.raises(ErrorValidacion):
        ContextoSimulacionV3(10, date(2026, 9, 10), 0, Decimal("0"))


def test_mapea_y_ordena_cuotas():
    snapshots = mapear_cuotas_a_snapshot_v3(
        [cuota(2, venc=date(2026, 10, 1)), cuota(1, venc=date(2026, 9, 1))]
    )
    assert tuple(s.numero_cuota for s in snapshots) == (1, 2)
    assert snapshots[0].saldo.interes == Decimal("20000.00")


def test_mapeo_preserva_estado_parcial_y_flag_historico():
    snapshots = mapear_cuotas_a_snapshot_v3(
        [cuota(1, estado="PARCIAL", capital="70000", interes="0", parcial=True)]
    )
    assert snapshots[0].estado == "PARCIAL"
    assert snapshots[0].tuvo_pago_parcial is True
    assert snapshots[0].saldo.capital == Decimal("70000.00")


def test_simulacion_parcial_mora_interes_capital_en_orden():
    plan = simular_desde_cuotas_v3(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 10),
        revision_prestamo=1,
        monto_recibido=Decimal("50000"),
        cuotas=[cuota(1)],
    )
    assert plan.aplicado_interes == Decimal("20000.00")
    assert plan.monto_a_capital == Decimal("30000.00")
    assert plan.excedente.monto == Decimal("0.00")
    assert plan.tipo.value == "PARCIAL"


def test_simulacion_complementa_parcial_y_continua_siguiente_cuota():
    plan = simular_desde_cuotas_v3(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 20),
        revision_prestamo=2,
        monto_recibido=Decimal("80000"),
        cuotas=[
            cuota(1, estado="PARCIAL", interes="0", capital="70000", parcial=True),
            cuota(2, interes="25000", capital="90000"),
        ],
    )
    assert plan.tipo.value == "COMPLEMENTO"
    assert [(a.cuota_id, a.concepto.value, a.monto) for a in plan.aplicaciones] == [
        (1, "CAPITAL", Decimal("70000.00")),
        (2, "INTERES", Decimal("10000.00")),
    ]


def test_simulacion_no_confunde_dos_cuotas_con_un_unico_arrastre():
    plan = simular_desde_cuotas_v3(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 20),
        revision_prestamo=3,
        monto_recibido=Decimal("50000"),
        cuotas=[
            cuota(1, interes="10000", capital="20000", mora="500"),
            cuota(2, interes="20000", capital="50000", mora="1000"),
        ],
    )
    assert [(a.cuota_id, a.concepto.value, a.monto) for a in plan.aplicaciones] == [
        (1, "MORA", Decimal("500.00")),
        (1, "INTERES", Decimal("10000.00")),
        (1, "CAPITAL", Decimal("20000.00")),
        (2, "MORA", Decimal("1000.00")),
        (2, "INTERES", Decimal("18500.00")),
    ]


def test_simulacion_excedente_no_decide_rai_rni():
    plan = simular_desde_cuotas_v3(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 10),
        revision_prestamo=1,
        monto_recibido=Decimal("200000"),
        cuotas=[cuota(1)],
    )
    assert plan.excedente.monto == Decimal("80000.00")
    assert plan.excedente.tratamiento is None


def test_simulacion_no_modifica_objetos_de_entrada():
    cuotas = [cuota(1)]
    antes = tuple(c.__dict__.copy() for c in cuotas)
    simular_desde_cuotas_v3(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 10),
        revision_prestamo=1,
        monto_recibido=Decimal("50000"),
        cuotas=cuotas,
    )
    despues = tuple(c.__dict__.copy() for c in cuotas)
    assert despues == antes


def test_plan_v3_es_determinista_para_mismo_snapshot():
    cuotas = [cuota(1), cuota(2, interes="25000", capital="90000")]
    kwargs = dict(
        prestamo_id=10,
        fecha_valor=date(2026, 9, 10),
        revision_prestamo=4,
        monto_recibido=Decimal("50000"),
        cuotas=cuotas,
    )
    assert simular_desde_cuotas_v3(**kwargs) == simular_desde_cuotas_v3(**kwargs)


def test_revision_negativa_se_rechaza_antes_del_motor():
    with pytest.raises(ErrorValidacion):
        simular_desde_cuotas_v3(
            prestamo_id=10,
            fecha_valor=date(2026, 9, 10),
            revision_prestamo=-1,
            monto_recibido=Decimal("50000"),
            cuotas=[cuota(1)],
        )


def test_simulacion_rechaza_cuota_duplicada_por_id():
    with pytest.raises(ErrorValidacion):
        simular_desde_cuotas_v3(
            prestamo_id=10,
            fecha_valor=date(2026, 9, 20),
            revision_prestamo=1,
            monto_recibido=Decimal("100"),
            cuotas=[
                cuota(1, cid=101, venc=date(2026, 9, 10)),
                cuota(2, cid=101, venc=date(2026, 9, 20)),
            ],
        )
