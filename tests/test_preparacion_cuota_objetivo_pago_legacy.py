"""Pruebas de la preparación pura de la cuota objetivo del pago Legacy."""
from decimal import Decimal
from types import SimpleNamespace

from aplicacion.servicios.preparacion_cuota_objetivo_pago_legacy import (
    PreparadorCuotaObjetivoPagoLegacy,
)


def _cuota(*, cuota_id=12, tuvo_pago_parcial=False, fue_mora=False, fue_recalculada=True):
    return SimpleNamespace(
        id=cuota_id,
        tuvo_pago_parcial=tuvo_pago_parcial,
        fue_mora=fue_mora,
        fue_recalculada=fue_recalculada,
        mora_pendiente=Decimal("10.00"),
        interes_pendiente=Decimal("30.00"),
        capital_pendiente=Decimal("100.00"),
    )


def test_prepara_saldo_objetivo_interes_extra_e_imputaciones_legacy():
    cuota = _cuota()
    deuda = {
        "mora_nueva": Decimal("10.00"),
        "cuota_interes": Decimal("30.00"),
        "interes_extra": Decimal("5.00"),
        "cuota_capital": Decimal("100.00"),
    }

    resultado = PreparadorCuotaObjetivoPagoLegacy().preparar(
        cuota_objetivo=cuota,
        deuda=deuda,
        restante_mora=Decimal("2.00"),
        restante_interes=Decimal("10.00"),
        restante_capital=Decimal("20.00"),
        aplicado_mora=Decimal("15.00"),
        aplicado_interes=Decimal("20.00"),
        aplicado_capital=Decimal("40.00"),
        monto_a_capital=Decimal("12.50"),
        tasa_mensual=Decimal("0.02"),
        interes_compensatorio_post_vencimiento=True,
    )

    assert resultado.actualizacion == {
        "cuota_id": 12,
        "estado": "PARCIAL",
        "interes_pendiente": Decimal("25.00"),
        "capital_pendiente": Decimal("80.00"),
        "mora_pendiente": Decimal("8.00"),
        "fue_mora": True,
        "tuvo_pago_parcial": True,
        "fue_recalculada": True,
    }
    assert resultado.interes_extra_generado == Decimal("1.60")
    # La extracción conserva los importes y el orden que el Legacy persistía.
    assert resultado.imputaciones == (
        {"cuota_id": 12, "concepto": "MORA", "monto": Decimal("15.00")},
        {"cuota_id": 12, "concepto": "INTERES", "monto": Decimal("20.00")},
        {"cuota_id": 12, "concepto": "CAPITAL", "monto": Decimal("52.50")},
    )
    # Preparar la actualización no modifica la entidad que llegó al servicio.
    assert cuota.fue_mora is False
    assert cuota.tuvo_pago_parcial is False
    assert cuota.capital_pendiente == Decimal("100.00")


def test_prepara_cuota_pagada_y_no_genera_interes_si_la_politica_no_lo_indica():
    cuota = _cuota(cuota_id=4, fue_mora=True, fue_recalculada=False)
    deuda = {
        "mora_nueva": Decimal("0.00"),
        "cuota_interes": Decimal("10.00"),
        "interes_extra": Decimal("0.00"),
        "cuota_capital": Decimal("20.00"),
    }

    resultado = PreparadorCuotaObjetivoPagoLegacy().preparar(
        cuota_objetivo=cuota,
        deuda=deuda,
        restante_mora=Decimal("0.00"),
        restante_interes=Decimal("10.00"),
        restante_capital=Decimal("20.00"),
        aplicado_mora=Decimal("0.00"),
        aplicado_interes=Decimal("10.00"),
        aplicado_capital=Decimal("20.00"),
        monto_a_capital=Decimal("0.00"),
        tasa_mensual=Decimal("0.02"),
        interes_compensatorio_post_vencimiento=False,
    )

    assert resultado.actualizacion == {
        "cuota_id": 4,
        "estado": "PAGADA",
        "interes_pendiente": Decimal("0.00"),
        "capital_pendiente": Decimal("0.00"),
        "mora_pendiente": Decimal("0.00"),
        "fue_mora": True,
        "tuvo_pago_parcial": False,
        "fue_recalculada": False,
    }
    assert resultado.interes_extra_generado == Decimal("0.00")
    assert resultado.imputaciones == (
        {"cuota_id": 4, "concepto": "INTERES", "monto": Decimal("10.00")},
        {"cuota_id": 4, "concepto": "CAPITAL", "monto": Decimal("20.00")},
    )
