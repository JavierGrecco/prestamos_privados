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
    calcular_tasa_neta_benchmark_usd,
    comparar_escenarios_benchmark,
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

    # La TEA 12% convertida a TEM se aplica sobre capital constante sin capitalizar.
    assert resultado.interes_debido_carencia_usd == Decimal("113.88")
    assert resultado.interes_no_cobrado_carencia_usd == Decimal("0.00")
    assert sum(
        (cuota.interes_carencia_usd for cuota in resultado.cuotas),
        Decimal("0.00"),
    ) == Decimal("113.88")
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

    # El interés de referencia simple no alcanza la TEA anual completa porque no capitaliza.
    assert resultado.interes_referencia_carencia_usd == Decimal("113.88")
    assert resultado.interes_no_cobrado_carencia_usd == Decimal("113.88")
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


def test_admite_supuestos_iniciales_sin_presentarlos_como_observados():
    cotizacion = CotizacionUnidad(
        fecha_cotizacion=date(2026, 1, 1),
        ars_por_usd=Decimal("1000"),
        fuente="Supuesto del usuario",
        lado="VENDEDOR",
        naturaleza="SUPUESTO",
    )
    resultado = _simular(cotizacion_inicial=cotizacion)

    assert resultado.cotizacion_inicial.naturaleza == "SUPUESTO"


def test_rechaza_cotizacion_float_para_evitar_aritmetica_binaria():
    with pytest.raises(ErrorValidacion, match="Decimal"):
        CotizacionUnidad(
            fecha_cotizacion=date(2026, 1, 1),
            ars_por_usd=1000.0,
            fuente="MEP",
            lado="VENDEDOR",
        )


def test_rechaza_valor_de_cotizacion_no_validado_en_calendario():
    fecha = date(2026, 2, 28)
    with pytest.raises(ErrorValidacion, match="CotizacionUnidad"):
        _simular(cotizaciones_por_vencimiento={fecha: Decimal("1000")})


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


def test_autoprestamo_reinvierte_benchmark_durante_carencia_en_base_objetivo():
    resultado = _simular(
        tasa_anual_usd=Decimal("0.12"),
        meses_carencia=12,
        tratamiento_carencia=TratamientoCarencia.SIN_INTERES,
        modo_reposicion_interna=True,
    )

    assert resultado.capital_inicial_usd == Decimal("1000.00")
    assert resultado.capital_objetivo_fin_carencia_usd == Decimal("1120.00")
    assert resultado.rendimiento_benchmark_carencia_usd == Decimal("120.00")
    assert resultado.interes_referencia_carencia_usd == Decimal("113.88")
    assert resultado.interes_debido_carencia_usd == Decimal("0.00")
    assert resultado.interes_no_cobrado_carencia_usd == Decimal("0.00")
    assert resultado.brecha_rendimiento_benchmark_carencia_usd == Decimal("0.00")
    assert resultado.modo_reposicion_interna
    assert resultado.cuotas[0].capital_inicial_usd == Decimal("1120.00")
    assert all(c.interes_carencia_usd == Decimal("0.00") for c in resultado.cuotas)
    assert resultado.cuotas[-1].saldo_capital_usd == Decimal("0.00")
    assert resultado.rendimiento_anualizado_usd is not None
    assert Decimal("0.10") < resultado.rendimiento_anualizado_usd < Decimal("0.14")


def test_prestamo_externo_muestra_brecha_sin_agregarla_automaticamente_a_la_deuda():
    resultado = _simular(
        tasa_anual_usd=Decimal("0.08"),
        tasa_benchmark_usd=Decimal("0.12"),
        modalidad_benchmark=ModalidadTasa.TEA,
        meses_carencia=12,
        tratamiento_carencia=TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO,
        modo_reposicion_interna=False,
    )

    assert resultado.capital_objetivo_fin_carencia_usd == Decimal("1000.00")
    assert resultado.rendimiento_benchmark_carencia_usd == Decimal("120.00")
    assert Decimal("0.00") < resultado.interes_debido_carencia_usd < Decimal("100.00")
    assert resultado.brecha_rendimiento_benchmark_carencia_usd == (
        Decimal("120.00") - resultado.interes_debido_carencia_usd
    )
    assert resultado.tasa_anual_usd == Decimal("0.08")
    assert resultado.tasa_benchmark_usd == Decimal("0.12")
    assert resultado.cuotas[0].capital_inicial_usd == Decimal("1000.00")
    assert any("rendimiento compuesto del benchmark supera" in aviso for aviso in resultado.advertencias)


def test_autoprestamo_sin_carencia_no_agrega_rendimiento_extra_a_la_base():
    resultado = _simular(
        tasa_anual_usd=Decimal("0.12"),
        meses_carencia=0,
        modo_reposicion_interna=True,
    )

    assert resultado.capital_objetivo_fin_carencia_usd == Decimal("1000.00")
    assert resultado.rendimiento_benchmark_carencia_usd == Decimal("0.00")
    assert resultado.brecha_rendimiento_benchmark_carencia_usd == Decimal("0.00")

def test_autoprestamo_rechaza_sumar_interes_simple_sobre_rendimiento_reinvertido():
    with pytest.raises(ErrorValidacion, match="use SIN_INTERES"):
        _simular(
            tasa_anual_usd=Decimal("0.12"),
            meses_carencia=12,
            tratamiento_carencia=TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO,
            modo_reposicion_interna=True,
        )


def test_autoprestamo_exige_coincidencia_entre_benchmark_y_tasa_del_plan():
    with pytest.raises(ErrorValidacion, match="debe coincidir"):
        _simular(
            tasa_anual_usd=Decimal("0.08"),
            tasa_benchmark_usd=Decimal("0.12"),
            meses_carencia=12,
            tratamiento_carencia=TratamientoCarencia.SIN_INTERES,
            modo_reposicion_interna=True,
        )


def test_autoprestamo_reinvierte_cuotas_y_reconcilia_con_inversion_original():
    resultado = _simular(
        tasa_anual_usd=Decimal("0.12"),
        tasa_benchmark_usd=Decimal("0.12"),
        modalidad_benchmark=ModalidadTasa.TEA,
        meses_carencia=12,
        plazo_amortizacion_meses=24,
        tratamiento_carencia=TratamientoCarencia.SIN_INTERES,
        modo_reposicion_interna=True,
    )

    assert resultado.valor_original_invertido_fin_plazo_usd > Decimal("1400.00")
    assert resultado.valor_cuotas_reinvertidas_fin_plazo_usd > Decimal("1400.00")
    assert abs(resultado.brecha_valor_final_benchmark_usd) <= Decimal("1.00")
    assert resultado.cuotas[-1].fecha_vencimiento == date(2029, 1, 31)


def test_prestamo_externo_por_debajo_del_benchmark_deja_brecha_final_negativa():
    resultado = _simular(
        tasa_anual_usd=Decimal("0.08"),
        tasa_benchmark_usd=Decimal("0.12"),
        modalidad_benchmark=ModalidadTasa.TEA,
        meses_carencia=12,
        plazo_amortizacion_meses=24,
        tratamiento_carencia=TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO,
        modo_reposicion_interna=False,
    )

    assert resultado.tasa_anual_usd == Decimal("0.08")
    assert resultado.tasa_benchmark_usd == Decimal("0.12")
    assert (
        resultado.valor_cuotas_reinvertidas_fin_plazo_usd
        < resultado.valor_original_invertido_fin_plazo_usd
    )
    assert resultado.brecha_valor_final_benchmark_usd < Decimal("0.00")


def test_cotizaciones_ars_no_alteran_brecha_final_del_benchmark_en_usd():
    fechas = [
        date(2027, 1, 31) + relativedelta(months=i)
        for i in range(1, 13)
    ]
    resultado_sin_fx = _simular(
        meses_carencia=12,
        tasa_anual_usd=Decimal("0.12"),
        tasa_benchmark_usd=Decimal("0.12"),
        modo_reposicion_interna=True,
    )
    resultado_con_fx = _simular(
        meses_carencia=12,
        tasa_anual_usd=Decimal("0.12"),
        tasa_benchmark_usd=Decimal("0.12"),
        modo_reposicion_interna=True,
        cotizaciones_por_vencimiento={
            fecha: _cotizacion(fecha, str(1000 + 50 * i))
            for i, fecha in enumerate(fechas, start=1)
        },
    )

    assert (
        resultado_sin_fx.valor_original_invertido_fin_plazo_usd
        == resultado_con_fx.valor_original_invertido_fin_plazo_usd
    )
    assert (
        resultado_sin_fx.valor_cuotas_reinvertidas_fin_plazo_usd
        == resultado_con_fx.valor_cuotas_reinvertidas_fin_plazo_usd
    )
    assert (
        resultado_sin_fx.brecha_valor_final_benchmark_usd
        == resultado_con_fx.brecha_valor_final_benchmark_usd
    )


def test_autoprestamo_reconcilia_valor_final_con_convencion_actual365():
    resultado = _simular(
        tasa_anual_usd=Decimal("0.12"),
        tasa_benchmark_usd=Decimal("0.12"),
        modalidad_benchmark=ModalidadTasa.TEA,
        convencion_dias=ConvencionDias.ACTUAL_365,
        meses_carencia=12,
        plazo_amortizacion_meses=24,
        tratamiento_carencia=TratamientoCarencia.SIN_INTERES,
        modo_reposicion_interna=True,
    )

    assert resultado.valor_original_invertido_fin_plazo_usd > Decimal("1400.00")
    assert resultado.valor_cuotas_reinvertidas_fin_plazo_usd > Decimal("1400.00")
    assert abs(resultado.brecha_valor_final_benchmark_usd) <= Decimal("2.00")

def test_tasa_neta_benchmark_descuenta_costos_e_impuesto_solo_sobre_retorno_positivo():
    neta = calcular_tasa_neta_benchmark_usd(
        tasa_bruta_anual=Decimal("0.04"),
        costos_anuales=Decimal("0.005"),
        impuesto_sobre_rendimiento_positivo=Decimal("0.20"),
    )
    assert neta == Decimal("0.028")

    escenario_negativo = calcular_tasa_neta_benchmark_usd(
        tasa_bruta_anual=Decimal("0.002"),
        costos_anuales=Decimal("0.01"),
        impuesto_sobre_rendimiento_positivo=Decimal("0.25"),
    )
    assert escenario_negativo == Decimal("-0.008")


@pytest.mark.parametrize(
    ("bruta", "costos", "impuesto"),
    [
        (Decimal("NaN"), Decimal("0"), Decimal("0")),
        (Decimal("0.04"), Decimal("-0.01"), Decimal("0")),
        (Decimal("0.04"), Decimal("0"), Decimal("1.01")),
        (Decimal("1.01"), Decimal("0"), Decimal("0")),
    ],
)
def test_tasa_neta_benchmark_rechaza_supuestos_fuera_de_rango(bruta, costos, impuesto):
    with pytest.raises(ErrorValidacion):
        calcular_tasa_neta_benchmark_usd(
            tasa_bruta_anual=bruta,
            costos_anuales=costos,
            impuesto_sobre_rendimiento_positivo=impuesto,
        )


def test_escenarios_benchmark_comparan_el_mismo_flujo_y_admiten_perdida_alternativa():
    capital = Decimal("1000.00")
    desembolso = date(2026, 1, 31)
    flujos = (
        (date(2026, 2, 28), Decimal("360.00")),
        (date(2026, 3, 31), Decimal("360.00")),
        (date(2026, 4, 30), Decimal("360.00")),
    )
    resultados = comparar_escenarios_benchmark(
        capital_inicial_usd=capital,
        fecha_desembolso=desembolso,
        flujos_cuotas=flujos,
        escenarios={
            "Conservador": Decimal("-0.05"),
            "Base": Decimal("0.04"),
            "Alto": Decimal("0.08"),
        },
        modalidad_benchmark=ModalidadTasa.TEA,
        convencion_dias=ConvencionDias.MENSUAL,
    )

    assert [resultado.nombre for resultado in resultados] == [
        "Conservador", "Base", "Alto"
    ]
    assert resultados[0].valor_capital_original_final_usd < resultados[1].valor_capital_original_final_usd
    assert resultados[1].valor_capital_original_final_usd < resultados[2].valor_capital_original_final_usd
    assert resultados[0].valor_cuotas_reinvertidas_final_usd < resultados[1].valor_cuotas_reinvertidas_final_usd
    assert resultados[1].valor_cuotas_reinvertidas_final_usd < resultados[2].valor_cuotas_reinvertidas_final_usd
    for resultado in resultados:
        assert resultado.brecha_final_usd == (
            resultado.valor_cuotas_reinvertidas_final_usd
            - resultado.valor_capital_original_final_usd
        )


def test_escenarios_benchmark_rechazan_tasa_que_desploma_el_capital_a_cero():
    with pytest.raises(ErrorValidacion, match="mayor a -100%"):
        comparar_escenarios_benchmark(
            capital_inicial_usd=Decimal("1000"),
            fecha_desembolso=date(2026, 1, 31),
            flujos_cuotas=((date(2026, 2, 28), Decimal("100")),),
            escenarios={"Inválido": Decimal("-1")},
            modalidad_benchmark=ModalidadTasa.TEA,
            convencion_dias=ConvencionDias.MENSUAL,
        )

