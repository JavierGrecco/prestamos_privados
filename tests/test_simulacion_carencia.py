"""Regresiones del simulador puro de carencia y flujo de caja."""
from datetime import date
from decimal import Decimal

import pytest

from ui.pagina_simulador_carencia import (
    _csv_calendario,
    _csv_comparacion,
    _parsear_decimal_es,
)

from dominio import (
    ConvencionDias,
    ErrorValidacion,
    ModalidadTasa,
    SistemaAmortizacion,
    TratamientoCarencia,
    generar_tabla,
    simular_carencia,
)


CAPITAL = Decimal("1000000")
TASA = Decimal("0.36")
FECHA = date(2026, 1, 31)


def _simular(tratamiento: TratamientoCarencia, **overrides):
    args = {
        "capital": CAPITAL,
        "tasa_anual": TASA,
        "modalidad": ModalidadTasa.TNA,
        "convencion": ConvencionDias.MENSUAL,
        "fecha_desembolso": FECHA,
        "meses_carencia": 12,
        "plazo_amortizacion_meses": 24,
        "sistema": SistemaAmortizacion.FRANCES,
        "tratamiento": tratamiento,
    }
    args.update(overrides)
    return simular_carencia(**args)


def test_carencia_cero_reproduce_la_tabla_regular_existente():
    resultado = _simular(
        TratamientoCarencia.SIN_INTERES,
        meses_carencia=0,
        fecha_desembolso=date(2026, 1, 1),
    )
    tabla = generar_tabla(
        capital=CAPITAL,
        tasa_anual=TASA,
        modalidad=ModalidadTasa.TNA,
        meses=24,
        fecha_inicio=date(2026, 1, 1),
        sistema=SistemaAmortizacion.FRANCES,
    )

    assert resultado.interes_simple_referencia_carencia == Decimal("0.00")
    assert resultado.costo_total_intereses_deudor == sum(
        (fila["interes"] for fila in tabla), start=Decimal("0.00")
    )
    assert [
        (cuota.vencimiento, cuota.cuota_base, cuota.saldo_capital)
        for cuota in resultado.cuotas
    ] == [
        (fila["vencimiento"], fila["cuota"], fila["saldo"])
        for fila in tabla
    ]


def test_interes_diferido_simple_en_primera_cuota_no_aumenta_el_capital():
    resultado = _simular(TratamientoCarencia.DIFERIR_SIMPLE_PRIMERA_CUOTA)

    assert resultado.interes_simple_referencia_carencia == Decimal("360000.00")
    assert resultado.interes_carencia_diferido == Decimal("360000.00")
    assert resultado.interes_carencia_capitalizado == Decimal("0.00")
    assert resultado.capital_amortizable_inicio == CAPITAL
    assert resultado.cuotas[0].interes_carencia_agregado == Decimal("360000.00")
    assert all(c.saldo_capital <= CAPITAL for c in resultado.cuotas)
    assert resultado.total_pagado_deudor == sum(
        (c.importe_total for c in resultado.cuotas), start=Decimal("0.00")
    )
    assert resultado.rendimiento_anualizado_prestamista is not None


def test_interes_diferido_distribuido_no_genera_interes_sobre_interes():
    resultado = _simular(TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO)

    assert sum(
        (c.interes_carencia_agregado for c in resultado.cuotas),
        start=Decimal("0.00"),
    ) == Decimal("360000.00")
    assert all(c.capital_inicial <= CAPITAL for c in resultado.cuotas)
    assert resultado.costo_total_intereses_deudor == Decimal("777137.96")


def test_intereses_pagados_durante_carencia_no_se_acumulan_al_capital():
    resultado = _simular(TratamientoCarencia.PAGAR_INTERES_DURANTE_CARENCIA)

    assert resultado.interes_carencia_pagado_durante == Decimal("360000.00")
    assert resultado.interes_carencia_diferido == Decimal("0.00")
    assert resultado.capital_amortizable_inicio == CAPITAL
    assert len([f for f in resultado.flujos_prestamista if FECHA < f[0] <= resultado.fecha_fin_carencia]) == 12
    assert resultado.total_pagado_deudor == Decimal("1777137.96")


def test_sin_interes_muestra_costo_de_oportunidad_sin_cobrarlo():
    resultado = _simular(TratamientoCarencia.SIN_INTERES)

    assert resultado.interes_carencia_no_cobrado == Decimal("360000.00")
    assert resultado.interes_carencia_diferido == Decimal("0.00")
    assert resultado.costo_total_intereses_deudor == Decimal("417137.96")


def test_capitalizacion_requiere_opt_in_de_escenario_y_advierte():
    with pytest.raises(ErrorValidacion, match="solo"):
        _simular(TratamientoCarencia.CAPITALIZAR_AL_FIN)

    resultado = _simular(
        TratamientoCarencia.CAPITALIZAR_AL_FIN,
        permitir_capitalizacion_solo_analisis=True,
    )
    assert resultado.solo_analisis is True
    assert resultado.capital_amortizable_inicio == Decimal("1360000.00")
    assert resultado.interes_carencia_capitalizado == Decimal("360000.00")
    assert resultado.rendimiento_anualizado_prestamista is not None
    assert any("validez jurídica" in a for a in resultado.advertencias)


def test_capitalizacion_con_tea_se_rechaza_hasta_definir_semantica():
    with pytest.raises(ErrorValidacion, match="capitalización con TEA"):
        _simular(
            TratamientoCarencia.CAPITALIZAR_AL_FIN,
            modalidad=ModalidadTasa.TEA,
            permitir_capitalizacion_solo_analisis=True,
        )


def test_simulacion_integral_rechaza_convencion_de_dias_no_soportada():
    with pytest.raises(ErrorValidacion, match="requiere convención MENSUAL"):
        _simular(
            TratamientoCarencia.SIN_INTERES,
            convencion=ConvencionDias.ACTUAL_365,
        )


def test_fecha_fin_carencia_y_primer_vencimiento_explicitos_en_salida():
    resultado = _simular(TratamientoCarencia.SIN_INTERES)

    assert resultado.fecha_fin_carencia == date(2027, 1, 31)
    assert resultado.fecha_primer_vencimiento == date(2027, 2, 28)
    assert resultado.cuotas[1].vencimiento == date(2027, 3, 31)


def test_teas_con_interes_diferido_incluye_advertencia_de_rentabilidad():
    resultado = _simular(
        TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO,
        tasa_anual=Decimal("0.30"),
        modalidad=ModalidadTasa.TEA,
        fecha_desembolso=date(2026, 1, 1),
    )

    assert any("rendimiento efectivo" in a for a in resultado.advertencias)
    assert resultado.rendimiento_anualizado_prestamista is not None


def test_csv_comparacion_expone_tratamientos_costos_y_advertencias():
    resultados = {
        tratamiento.value: simular_carencia(
            capital=CAPITAL,
            tasa_anual=TASA,
            modalidad=ModalidadTasa.TNA,
            convencion=ConvencionDias.MENSUAL,
            fecha_desembolso=FECHA,
            meses_carencia=12,
            plazo_amortizacion_meses=24,
            sistema=SistemaAmortizacion.FRANCES,
            tratamiento=tratamiento,
            permitir_capitalizacion_solo_analisis=(
                tratamiento == TratamientoCarencia.CAPITALIZAR_AL_FIN
            ),
        )
        for tratamiento in TratamientoCarencia
    }
    csv = _csv_comparacion(resultados).decode("utf-8-sig")

    assert csv.startswith("tratamiento;fecha_desembolso;meses_carencia")
    assert csv.count("\n") > 2
    assert "\\n" not in csv
    assert "Sin interés durante la carencia" in csv
    assert "Diferir interés simple a la primera cuota" in csv
    assert "capitalizado_solo_analisis" in csv
    assert "true" in csv


def test_csv_calendario_incluye_vencimientos_y_componentes_separados():
    resultado = _simular(TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO)
    csv = _csv_calendario(resultado).decode("utf-8-sig")

    assert csv.startswith("numero_cuota;fecha_vencimiento;capital_inicial")
    assert csv.count("\n") > 2
    assert "\\n" not in csv
    assert "interes_carencia_agregado" in csv
    assert date(2027, 2, 28).isoformat() in csv
    assert "importe_total" in csv


@pytest.mark.parametrize(
    ("texto", "esperado", "decimales"),
    [
        ("1.000.000,50", "1000000.50", 2),
        ("1000000,50", "1000000.50", 2),
        ("1000000.50", "1000000.50", 2),
        ("1.000.000", "1000000", 2),
        ("36,5000", "36.5000", 4),
        ("36.5", "36.5", 4),
        ("0.001", "0.001", 4),
        ("1.000", "1000", 2),
    ],
)
def test_entrada_decimal_es_se_parsea_sin_float(texto, esperado, decimales):
    valor = _parsear_decimal_es(
        texto,
        etiqueta="valor",
        minimo=Decimal("0"),
        maximo=Decimal("1000000000000"),
        decimales_maximos=decimales,
    )
    assert valor == Decimal(esperado)
    assert isinstance(valor, Decimal)


@pytest.mark.parametrize(
    ("texto", "max_decimales"),
    [
        ("", 2),
        ("NaN", 2),
        ("Infinity", 2),
        ("1.00,1", 2),
        ("1.000,123", 2),
        ("1,2,3", 2),
        ("12.34.567", 2),
        ("abc", 2),
        ("100,001", 2),
    ],
)
def test_entrada_decimal_es_rechaza_texto_ambiguo_o_precision_invalida(
    texto, max_decimales
):
    with pytest.raises(ErrorValidacion):
        _parsear_decimal_es(
            texto,
            etiqueta="capital",
            minimo=Decimal("0"),
            maximo=Decimal("1000000000000"),
            decimales_maximos=max_decimales,
        )
