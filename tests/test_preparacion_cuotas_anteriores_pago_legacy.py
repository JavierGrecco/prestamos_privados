"""Pruebas del plan de aplicación sobre las cuotas anteriores a la objetivo."""
from decimal import Decimal
from types import SimpleNamespace

from aplicacion.servicios.preparacion_cuotas_anteriores_pago_legacy import (
    PreparadorCuotasAnterioresPagoLegacy,
)
from dominio.politica_pago import PoliticaImputacionPago


def _cuota(
    cuota_id: int,
    *,
    mora: str,
    interes: str,
    capital: str,
    tuvo_pago_parcial: bool = False,
    fue_mora: bool = True,
    fue_recalculada: bool = False,
):
    return SimpleNamespace(
        id=cuota_id,
        total_pendiente=Decimal(mora) + Decimal(interes) + Decimal(capital),
        mora_pendiente=Decimal(mora),
        interes_pendiente=Decimal(interes),
        capital_pendiente=Decimal(capital),
        tuvo_pago_parcial=tuvo_pago_parcial,
        fue_mora=fue_mora,
        fue_recalculada=fue_recalculada,
    )


def test_prepara_cuotas_anteriores_respetando_mora_interes_capital():
    saldada = _cuota(0, mora="0", interes="0", capital="0", fue_mora=False)
    anterior_1 = _cuota(1, mora="10", interes="20", capital="50")
    anterior_2 = _cuota(2, mora="5", interes="30", capital="20")
    objetivo = _cuota(3, mora="99", interes="99", capital="99")
    posterior = _cuota(4, mora="7", interes="8", capital="9")
    cuotas = (saldada, anterior_1, anterior_2, objetivo, posterior)

    resultado = PreparadorCuotasAnterioresPagoLegacy().preparar(
        cuotas=cuotas,
        cuota_objetivo=objetivo,
        aplicado_mora=Decimal("25"),
        aplicado_interes=Decimal("25"),
        aplicado_capital=Decimal("30"),
        orden_waterfall=PoliticaImputacionPago.canonica().orden_waterfall,
    )

    assert [cambio["cuota_id"] for cambio in resultado.actualizaciones] == [1, 2]
    assert resultado.actualizaciones[0] == {
        "cuota_id": 1,
        "estado": "PARCIAL",
        "interes_pendiente": Decimal("0"),
        "capital_pendiente": Decimal("20"),
        "mora_pendiente": Decimal("0"),
        "fue_mora": True,
        "tuvo_pago_parcial": True,
        "fue_recalculada": False,
    }
    assert resultado.actualizaciones[1] == {
        "cuota_id": 2,
        "estado": "PARCIAL",
        "interes_pendiente": Decimal("25"),
        "capital_pendiente": Decimal("20"),
        "mora_pendiente": Decimal("0"),
        "fue_mora": True,
        "tuvo_pago_parcial": True,
        "fue_recalculada": False,
    }
    assert resultado.restante_mora == Decimal("10")
    assert resultado.restante_interes == Decimal("0")
    assert resultado.restante_capital == Decimal("0")
    # El cálculo prepara cambios, no altera las cuotas de entrada.
    assert anterior_1.mora_pendiente == Decimal("10")
    assert anterior_2.interes_pendiente == Decimal("30")
    assert objetivo.mora_pendiente == Decimal("99")
    assert posterior.mora_pendiente == Decimal("7")


def test_cuota_anterior_completamente_pagada_se_marca_pagada():
    anterior = _cuota(
        1, mora="1", interes="2", capital="3", fue_mora=True
    )
    objetivo = _cuota(2, mora="0", interes="0", capital="10")

    resultado = PreparadorCuotasAnterioresPagoLegacy().preparar(
        cuotas=(anterior, objetivo),
        cuota_objetivo=objetivo,
        aplicado_mora=Decimal("1"),
        aplicado_interes=Decimal("2"),
        aplicado_capital=Decimal("3"),
        orden_waterfall=PoliticaImputacionPago.canonica().orden_waterfall,
    )

    assert resultado.actualizaciones == ({
        "cuota_id": 1,
        "estado": "PAGADA",
        "interes_pendiente": Decimal("0"),
        "capital_pendiente": Decimal("0"),
        "mora_pendiente": Decimal("0"),
        "fue_mora": True,
        "tuvo_pago_parcial": False,
        "fue_recalculada": False,
    },)
    assert resultado.restante_mora == Decimal("0")
    assert resultado.restante_interes == Decimal("0")
    assert resultado.restante_capital == Decimal("0")
