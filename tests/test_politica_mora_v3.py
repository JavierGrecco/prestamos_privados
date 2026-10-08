from datetime import date
from decimal import Decimal

import pytest

from dominio.excepciones import ErrorValidacion
from dominio.motor_pagos_v3 import ObligacionSnapshot
from dominio.politica_pago import BaseMoraPago
from dominio.politica_devengamiento_v3 import (
    ORIGEN_MORA_CONTRACTUAL,
    PoliticaMoraContractualV3,
    generar_mora_contractual,
)
from dominio.tipos import ConvencionDias


def obligacion(
    *,
    cuota_id=1,
    numero=1,
    vencimiento=date(2026, 11, 1),
    estado="PENDIENTE",
    mora="0",
    capital="156549.97",
    monto_mora_base="181549.97",
):
    return ObligacionSnapshot.desde_cuota_actual(
        cuota_id=cuota_id,
        numero_cuota=numero,
        vencimiento=vencimiento,
        estado=estado,
        tuvo_pago_parcial=estado == "PARCIAL",
        interes_pendiente=Decimal("0.00"),
        capital_pendiente=Decimal(capital),
        mora_pendiente=Decimal(mora),
        monto_mora_base=Decimal(monto_mora_base),
    )


def test_mora_contractual_reproduce_base_y_tiempo_legacy():
    politica = PoliticaMoraContractualV3()
    resultado = generar_mora_contractual(
        obligaciones=(obligacion(),),
        fecha_valor=date(2026, 12, 1),
        politica=politica,
    )

    evento = resultado[1][0]
    assert evento.monto == Decimal("7460.96")
    assert evento.base == Decimal("181549.97")
    assert evento.fecha_desde == date(2026, 11, 1)
    assert evento.fecha_hasta == date(2026, 12, 1)
    assert evento.dias == 30
    assert evento.convencion_dias is ConvencionDias.ACTUAL_365
    assert evento.origen == ORIGEN_MORA_CONTRACTUAL


@pytest.mark.parametrize(
    ("fecha_valor", "mora", "base"),
    [
        (date(2026, 11, 1), "0.00", "181549.97"),
        (date(2026, 10, 31), "0.00", "181549.97"),
        (date(2026, 12, 1), "7460.96", "181549.97"),
        (date(2026, 12, 1), "0.00", "0.00"),
    ],
)
def test_mora_contractual_no_duplica_o_no_genera_sin_condiciones(
    fecha_valor, mora, base
):
    resultado = generar_mora_contractual(
        obligaciones=(obligacion(mora=mora, monto_mora_base=base),),
        fecha_valor=fecha_valor,
        politica=PoliticaMoraContractualV3(),
    )
    if mora != "0.00" or base == "0.00" or fecha_valor <= date(2026, 11, 1):
        assert resultado == {}
    else:
        assert resultado


def test_mora_nueva_se_asigna_solo_a_la_primera_obligacion_pendiente():
    resultado = generar_mora_contractual(
        obligaciones=(
            obligacion(estado="PARCIAL", capital="70000"),
            obligacion(cuota_id=2, numero=2, vencimiento=date(2026, 12, 1)),
        ),
        fecha_valor=date(2027, 1, 1),
        politica=PoliticaMoraContractualV3(),
    )

    assert tuple(resultado) == (2,)


def test_mora_contractual_continua_desde_ultimo_corte():
    resultado = generar_mora_contractual(
        obligaciones=(obligacion(mora="7460.96"),),
        fecha_valor=date(2027, 1, 1),
        politica=PoliticaMoraContractualV3(),
        ultimo_hasta_por_cuota={1: date(2026, 12, 1)},
    )

    evento = resultado[1][0]
    assert evento.monto == Decimal("7709.66")
    assert evento.fecha_desde == date(2026, 12, 1)
    assert evento.fecha_hasta == date(2027, 1, 1)
    assert evento.dias == 31


def test_mora_historica_sin_corte_v3_no_se_duplica():
    resultado = generar_mora_contractual(
        obligaciones=(obligacion(mora="7460.96"),),
        fecha_valor=date(2027, 1, 1),
        politica=PoliticaMoraContractualV3(),
    )
    assert resultado == {}


def test_politica_mora_rechaza_convencion_no_contractual():
    with pytest.raises(ErrorValidacion, match="ACTUAL_365"):
        PoliticaMoraContractualV3(convencion_dias=ConvencionDias.MENSUAL)


def test_mora_puede_usar_capital_vencido_como_base():
    resultado = generar_mora_contractual(
        obligaciones=(obligacion(monto_mora_base="181549.97", capital="100000"),),
        fecha_valor=date(2026, 12, 1),
        politica=PoliticaMoraContractualV3(
            base=BaseMoraPago.CAPITAL_VENCIDO
        ),
    )

    assert resultado[1][0].base == Decimal("100000.00")
    assert resultado[1][0].monto == Decimal("4109.59")
