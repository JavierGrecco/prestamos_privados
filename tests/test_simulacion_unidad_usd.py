"""Pruebas del simulador analítico en unidades USD."""
from datetime import date
from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta

from dominio import (
    ConvencionDias,
    ErrorValidacion,
    ModalidadTasa,
    SistemaAmortizacion,
    TratamientoCarencia,
)
from dominio.simulacion_unidad_usd import (
    CotizacionUnidad,
    simular_unidad_usd,
)


def _cotizacion(fecha, tasa, naturaleza="PROYECTADA"):
    return CotizacionUnidad(
        fecha_cotizacion=fecha,
        ars_por_usd=Decimal(str(tasa)),
        fuente="MEP de prueba",
        lado="VENDEDOR",
        naturaleza=naturaleza,
        referencia="prueba determinista",
    )


def _simular(**cambios):
    args = {
        "capital_desembolso_ars": Decimal("1000000.00"),
        "cotizacion_inicial": _cotizacion(date(2026, 1, 30), "1000", "OBSERVADA"),
        "tasa_anual_usd": Decimal("0"),
        "modalidad_tasa": ModalidadTasa.TEA,
        "convencion_dias": ConvencionDias.MENSUAL,
        "sistema": SistemaAmortizacion.FRANCES,
        "fecha_desembolso": date(2026, 1, 31),
        "meses_carencia": 0,
        "plazo_amortizacion_meses": 12,
        "tratamiento_carencia": TratamientoCarencia.SIN_INTERES,
    }
    args.update(cambios)
    return simular_unidad_usd(**args)


def test_convierte_capital_ars_a_unidades_usd_con_cotizacion_base_fija():
    resultado = _simular()

    assert resultado.capital_desembolso_ars == Decimal("1000000.00")
    assert resultado.cotizacion_inicial.ars_por_usd == Decimal("1000")
    assert resultado.capital_inicial_usd == Decimal("1000.00")
    assert resultado.fecha_fin_carencia == date(2026, 1, 31)
    assert resultado.fecha_primer_vencimiento == date(2026, 2, 28)
    assert resultado.solo_analisis
    assert sum(
        (cuota.amortizacion_capital_usd for cuota in resultado.cuotas),
        Decimal("0.00"),
    ) == Decimal("1000.00")
    assert resultado.cuotas[-1].saldo_capital_usd == Decimal("0.00")


def test_cotizacion_por_pago_valua_ars_sin_cambiar_importes_programados_usd():
    sin_conversion = _simular()
    fechas = [date(2026, 1, 31) + relativedelta(months=i) for i in range(1, 13)]
    cotizaciones_1000 = {
        fecha: _cotizacion(fecha, "1000") for fecha in fechas
    }
    cotizaciones_1500 = {
        fecha: _cotizacion(fecha, "1500") for fecha in fechas
    }
    con_1000 = _simular(cotizaciones_por_vencimiento=cotizaciones_1000)
    con_1500 = _simular(cotizaciones_por_vencimiento=cotizaciones_1500)

    assert [c.importe_total_usd for c in con_1000.cuotas] == [
        c.importe_total_usd for c in con_1500.cuotas
    ] == [c.importe_total_usd for c in sin_conversion.cuotas]
    assert con_1000.total_equivalente_ars == Decimal("1000000.00")
    assert con_1500.total_equivalente_ars == Decimal("1500000.00")
    for cuota in con_1500.cuotas:
        assert cuota.cotizacion is not None
        assert cuota.equivalente_ars == (
            cuota.importe_total_usd * Decimal("1500")
        ).quantize(Decimal("0.01"))


def test_cotizaciones_independientes_no_reutilizan_el_tc_inicial():
    fechas = [date(2026, 1, 31) + relativedelta(months=i) for i in range(1, 13)]
    cotizaciones = {
        fecha: _cotizacion(fecha, str(1000 + 100 * indice))
        for indice, fecha in enumerate(fechas, start=1)
    }
    resultado = _simular(cotizaciones_por_vencimiento=cotizaciones)

    assert resultado.cotizacion_inicial.ars_por_usd == Decimal("1000")
    assert resultado.cuotas[0].cotizacion.ars_por_usd == Decimal("1100")
    assert resultado.cuotas[-1].cotizacion.ars_por_usd == Decimal("2200")
    assert resultado.cuotas[0].equivalente_ars != (
        resultado.cuotas[0].importe_total_usd * resultado.cotizacion_inicial.ars_por_usd
    ).quantize(Decimal("0.01"))


def test_interes_simple_diferido_en_usd_permanece_separado_del_capital():
    resultado = _simular(
        tasa_anual_usd=Decimal("0.12"),
        meses_carencia=12,
        tratamiento_carencia=TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO,
    )

    assert resultado.interes_debido_carencia_usd == Decimal("120.00")
    assert resultado.interes_no_cobrado_carencia_usd == Decimal("0.00")
    assert sum(
        (cuota.interes_carencia_usd for cuota in resultado.cuotas),
        Decimal("0.00"),
    ) == Decimal("120.00")
    assert sum(
        (cuota.amortizacion_capital_usd for cuota in resultado.cuotas),
        Decimal("0.00"),
    ) == Decimal("1000.00")
    assert resultado.cuotas[-1].saldo_capital_usd == Decimal("0.00")
    assert resultado.cuotas[0].capital_inicial_usd == Decimal("1000.00")
    assert sum(
        (cuota.importe_total_usd for cuota in resultado.cuotas), Decimal("0.00")
    ) == resultado.total_programado_usd


def test_sin_interes_no_suma_referencia_a_la_deuda():
    resultado = _simular(
        tasa_anual_usd=Decimal("0.12"),
        meses_carencia=12,
        tratamiento_carencia=TratamientoCarencia.SIN_INTERES,
    )

    assert resultado.interes_referencia_carencia_usd == Decimal("120.00")
    assert resultado.interes_no_cobrado_carencia_usd == Decimal("120.00")
    assert resultado.interes_debido_carencia_usd == Decimal("0.00")
    assert sum(
        (cuota.interes_carencia_usd for cuota in resultado.cuotas),
        Decimal("0.00"),
    ) == Decimal("0.00")


@pytest.mark.parametrize(
    "tratamiento",
    [
        TratamientoCarencia.PAGAR_INTERES_DURANTE_CARENCIA,
        TratamientoCarencia.CAPITALIZAR_AL_FIN,
    ],
)
def test_rechaza_modalidades_fuera_del_alcance_inicial(tratamiento):
    with pytest.raises(ErrorValidacion, match="Esta simulación admite"):
        _simular(tratamiento_carencia=tratamiento)


def test_rechaza_cotizacion_base_posterior_al_desembolso():
    with pytest.raises(ErrorValidacion, match="posterior al desembolso"):
        _simular(
            cotizacion_inicial=_cotizacion(date(2026, 2, 1), "1000", "OBSERVADA")
        )


@pytest.mark.parametrize("valor", [Decimal("0"), Decimal("-1")])
def test_rechaza_cotizaciones_nulas_o_negativas(valor):
    with pytest.raises(ErrorValidacion, match="mayor a cero"):
        _cotizar_invalida(valor)


def _cotizar_invalida(valor):
    return CotizacionUnidad(
        fecha_cotizacion=date(2026, 1, 1),
        ars_por_usd=valor,
        fuente="Fuente de prueba",
        lado="VENDEDOR",
    )


def test_rechaza_cotizaciones_sin_fuente_o_lado():
    with pytest.raises(ErrorValidacion, match="fuente"):
        CotizacionUnidad(date(2026, 1, 1), Decimal("1000"), "", "VENDEDOR")
    with pytest.raises(ErrorValidacion, match="lado"):
        CotizacionUnidad(date(2026, 1, 1), Decimal("1000"), "MEP", "")


def test_rechaza_cotizacion_asignada_a_fecha_que_no_es_vencimiento():
    with pytest.raises(ErrorValidacion, match="no corresponde a un vencimiento"):
        _simular(
            cotizaciones_por_vencimiento={
                date(2026, 1, 15): _cotizacion(date(2026, 1, 15), "1100")
            }
        )


def test_sin_todas_las_cotizaciones_no_finge_total_equivalente_ars():
    fechas = [date(2026, 1, 31) + relativedelta(months=i) for i in range(1, 13)]
    resultado = _simular(
        cotizaciones_por_vencimiento={fechas[0]: _cotizacion(fechas[0], "1100")}
    )

    assert resultado.cuotas[0].equivalente_ars is not None
    assert resultado.cuotas[1].equivalente_ars is None
    assert resultado.total_equivalente_ars is None
