"""Regresiones del simulador puro de carencia y flujo de caja."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from ui.pagina_simulador_carencia import (
    _csv_calendario,
    _csv_comparacion,
    _csv_escenarios_benchmark,
    _csv_backtest_indice_historico,
    _csv_unidad_usd,
    _cotizaciones_desde_editor,
    _csv_plantilla_cotizaciones,
    _leer_csv_cotizaciones,
    _csv_plantilla_indice_retorno_total,
    _leer_csv_indice_retorno_total,
    _csv_plantilla_precio_distribucion,
    _leer_csv_precio_distribucion,
    _parsear_decimal_es,
    _texto_csv_seguro,
)

from dominio import (
    ConvencionDias,
    ErrorValidacion,
    ModalidadTasa,
    SistemaAmortizacion,
    TratamientoCarencia,
    CotizacionUnidad,
    generar_tabla,
    simular_carencia,
    simular_unidad_usd,
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


@pytest.mark.parametrize(
    ("convencion", "interes_primer_periodo"),
    [
        (ConvencionDias.ACTUAL_365, Decimal("27616.44")),
        (ConvencionDias.ACTUAL_360, Decimal("28000.00")),
        (ConvencionDias.ACTUAL_ACTUAL, Decimal("27616.44")),
        (ConvencionDias.TREINTA_360, Decimal("30000.00")),
    ],
)
def test_simulacion_integral_usa_la_convencion_tambien_en_cuotas(
    convencion, interes_primer_periodo
):
    resultado = _simular(
        TratamientoCarencia.DIFERIR_SIMPLE_DISTRIBUIDO,
        convencion=convencion,
    )

    assert resultado.convencion is convencion
    assert resultado.fecha_primer_vencimiento == date(2027, 2, 28)
    assert resultado.cuotas[0].vencimiento == date(2027, 2, 28)
    assert resultado.cuotas[0].interes_periodo == interes_primer_periodo
    assert sum(
        (c.amortizacion_capital for c in resultado.cuotas),
        start=Decimal("0.00"),
    ) == resultado.capital_amortizable_inicio
    assert resultado.cuotas[-1].saldo_capital == Decimal("0.00")
    assert resultado.rendimiento_anualizado_prestamista is not None


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
        ("0.000001", "0.000001", 6),
        ("1.000,000001", "1000.000001", 6),
    ],
)
def test_entrada_decimal_local_se_parsea_sin_float(texto, esperado, decimales):
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
        ("1.234,56789", 4),
    ],
)
def test_entrada_decimal_local_rechaza_ambiguedad_y_precision(texto, max_decimales):
    with pytest.raises(ErrorValidacion):
        _parsear_decimal_es(
            texto,
            etiqueta="capital",
            minimo=Decimal("0"),
            maximo=Decimal("1000000000000"),
            decimales_maximos=max_decimales,
        )

def test_cotizaciones_por_cuota_conservan_decimal_fuente_lado_y_naturaleza():
    cuotas = [
        SimpleNamespace(numero=1, fecha_vencimiento=date(2027, 2, 28)),
        SimpleNamespace(numero=2, fecha_vencimiento=date(2027, 3, 31)),
    ]
    cotizaciones = _cotizaciones_desde_editor(
        [
            {
                "numero_cuota": 1,
                "fecha_vencimiento": "2027-02-28",
                "ars_por_usd": "1.250,500000",
                "fuente": "MEP / prueba",
                "lado": "VENDEDOR",
                "naturaleza": "OBSERVADA",
                "referencia": "evidencia-cuota-1",
            },
            {
                "numero_cuota": 2,
                "fecha_vencimiento": "2027-03-31",
                "ars_por_usd": "1.300,000000",
                "fuente": "escenario de prueba",
                "lado": "COMPRADOR",
                "naturaleza": "PROYECTADA",
                "referencia": "",
            },
        ],
        cuotas,
    )

    primera = cotizaciones[date(2027, 2, 28)]
    segunda = cotizaciones[date(2027, 3, 31)]
    assert primera.ars_por_usd == Decimal("1250.500000")
    assert isinstance(primera.ars_por_usd, Decimal)
    assert primera.fuente == "MEP / prueba"
    assert primera.lado == "VENDEDOR"
    assert primera.naturaleza == "OBSERVADA"
    assert primera.referencia == "evidencia-cuota-1"
    assert segunda.ars_por_usd == Decimal("1300.000000")
    assert segunda.lado == "COMPRADOR"
    assert segunda.naturaleza == "PROYECTADA"
    assert set(cotizaciones) == {date(2027, 2, 28), date(2027, 3, 31)}


def test_cotizaciones_por_cuota_ignoran_filas_completamente_vacias():
    cuota = SimpleNamespace(numero=1, fecha_vencimiento=date(2027, 2, 28))
    cotizaciones = _cotizaciones_desde_editor(
        [
            {
                "ars_por_usd": "",
                "fuente": "",
                "referencia": "",
                "lado": "VENDEDOR",
                "naturaleza": "OBSERVADA",
            }
        ],
        [cuota],
    )
    assert cotizaciones == {}


@pytest.mark.parametrize(
    ("fila", "mensaje"),
    [
        (
            {"ars_por_usd": "1.200,00", "fuente": "", "lado": "VENDEDOR",
             "naturaleza": "OBSERVADA", "referencia": ""},
            "indicá la fuente",
        ),
        (
            {"ars_por_usd": "", "fuente": "MEP", "lado": "VENDEDOR",
             "naturaleza": "OBSERVADA", "referencia": ""},
            "ingresá la cotización",
        ),
        (
            {"ars_por_usd": "1.200,1234567", "fuente": "MEP", "lado": "VENDEDOR",
             "naturaleza": "OBSERVADA", "referencia": ""},
            "máximo 6 decimales",
        ),
    ],
)
def test_cotizaciones_por_cuota_rechazan_filas_incompletas_o_invalidas(fila, mensaje):
    cuota = SimpleNamespace(numero=3, fecha_vencimiento=date(2027, 4, 30))
    with pytest.raises(ErrorValidacion, match=mensaje):
        _cotizaciones_desde_editor([fila], [cuota])


def test_cotizaciones_por_cuota_exigen_una_fila_por_vencimiento():
    with pytest.raises(ErrorValidacion, match="una fila por cada vencimiento"):
        _cotizaciones_desde_editor([], [
            SimpleNamespace(numero=1, fecha_vencimiento=date(2027, 2, 28))
        ])

def _resultado_base_cotizaciones():
    return SimpleNamespace(
        cuotas=(
            SimpleNamespace(numero=1, fecha_vencimiento=date(2027, 2, 28)),
            SimpleNamespace(numero=2, fecha_vencimiento=date(2027, 3, 31)),
            SimpleNamespace(numero=3, fecha_vencimiento=date(2027, 4, 30)),
        )
    )


def test_plantilla_csv_cotizaciones_incluye_fechas_fijas_y_decimal_local():
    plantilla = _csv_plantilla_cotizaciones(
        _resultado_base_cotizaciones(),
        lado_default="VENDEDOR",
    ).decode("utf-8-sig")

    assert plantilla.startswith(
        "numero_cuota;fecha_vencimiento;ars_por_usd;fuente;lado;naturaleza;referencia"
    )
    assert "1;2027-02-28;;;VENDEDOR;SUPUESTO;" in plantilla
    assert "2;2027-03-31;;;VENDEDOR;SUPUESTO;" in plantilla
    assert "3;2027-04-30;;;VENDEDOR;SUPUESTO;" in plantilla


def test_importar_csv_cotizaciones_admite_coma_decimal_y_filas_sin_dato():
    contenido = (
        "\ufeffnumero_cuota;fecha_vencimiento;ars_por_usd;fuente;lado;naturaleza;referencia\n"
        "1;2027-02-28;1.250,500000;MEP / especie declarada;VENDEDOR;OBSERVADA;evidencia-1\n"
        "2;2027-03-31;;;;SUPUESTO;\n"
    ).encode("utf-8")
    filas = _leer_csv_cotizaciones(
        contenido,
        _resultado_base_cotizaciones(),
        lado_default="COMPRADOR",
    )

    assert len(filas) == 3
    assert filas[0]["ars_por_usd"] == "1.250,500000"
    assert filas[0]["fuente"] == "MEP / especie declarada"
    assert filas[0]["lado"] == "VENDEDOR"
    assert filas[0]["naturaleza"] == "OBSERVADA"
    assert filas[0]["referencia"] == "evidencia-1"
    assert filas[1]["ars_por_usd"] == ""
    assert filas[1]["fecha_vencimiento"] == "2027-03-31"
    assert filas[2]["ars_por_usd"] == ""


@pytest.mark.parametrize(
    ("contenido", "mensaje"),
    [
        (
            b"numero_cuota,fecha_vencimiento,ars_por_usd,fuente,lado,naturaleza,referencia\n",
            "columnas requeridas",
        ),
        (
            b"numero_cuota;fecha_vencimiento;ars_por_usd;fuente;lado;naturaleza;referencia\n"
            b"9;2027-02-28;1200;MEP;VENDEDOR;OBSERVADA;\n",
            "no existe en el plan",
        ),
        (
            b"numero_cuota;fecha_vencimiento;ars_por_usd;fuente;lado;naturaleza;referencia\n"
            b"1;2027-03-31;1200;MEP;VENDEDOR;OBSERVADA;\n",
            "vence el 2027-02-28",
        ),
        (
            b"numero_cuota;fecha_vencimiento;ars_por_usd;fuente;lado;naturaleza;referencia\n"
            b"1;2027-02-28;1200;MEP;VENDEDOR;OBSERVADA;\n"
            b"1;2027-02-28;1210;MEP;VENDEDOR;OBSERVADA;\n",
            "repetida",
        ),
        (
            b"numero_cuota;fecha_vencimiento;ars_por_usd;fuente;lado;naturaleza;referencia\n"
            b"1;2027-02-28;1.200,000000;;VENDEDOR;OBSERVADA;\n",
            "fuente/instrumento es obligatoria",
        ),
        (
            b"numero_cuota;fecha_vencimiento;ars_por_usd;fuente;lado;naturaleza;referencia\n"
            b"1;2027-02-28;1.200,1234567;MEP;VENDEDOR;OBSERVADA;\n",
            "máximo 6 decimales",
        ),
    ],
)
def test_importar_csv_cotizaciones_rechaza_fechas_columnas_o_datos_invalidos(
    contenido, mensaje
):
    with pytest.raises(ErrorValidacion, match=mensaje):
        _leer_csv_cotizaciones(
            contenido,
            _resultado_base_cotizaciones(),
            lado_default="VENDEDOR",
        )


def test_importar_csv_cotizaciones_rechaza_cuota_duplicada_aunque_una_fila_este_vacia():
    contenido = (
        "numero_cuota;fecha_vencimiento;ars_por_usd;fuente;lado;naturaleza;referencia\n"
        "1;2027-02-28;;;;SUPUESTO;\n"
        "1;2027-02-28;1.200,000000;MEP;VENDEDOR;OBSERVADA;\n"
    ).encode("utf-8")
    with pytest.raises(ErrorValidacion, match="repetida"):
        _leer_csv_cotizaciones(
            contenido,
            _resultado_base_cotizaciones(),
            lado_default="VENDEDOR",
        )

@pytest.mark.parametrize(
    "texto",
    [
        "=1+1",
        " =HYPERLINK(\"https://example.invalid\")",
        "+SUM(1;2)",
        "-1+2",
        "@SUM(1;2)",
        "\t=1+1",
    ],
)
def test_csv_exporta_metadatos_con_prefijo_seguro_ante_formulas(texto):
    assert _texto_csv_seguro(texto).startswith("'")


def test_csv_exporta_metadatos_normales_sin_alterarlos():
    assert _texto_csv_seguro("MEP — fuente declarada") == "MEP — fuente declarada"
    assert _texto_csv_seguro("evidencia-2027-02") == "evidencia-2027-02"


def test_editor_rechaza_lado_de_cotizacion_fuera_del_catalogo():
    cuota = SimpleNamespace(numero=1, fecha_vencimiento=date(2027, 2, 28))
    with pytest.raises(ErrorValidacion, match="lado debe ser VENDEDOR o COMPRADOR"):
        _cotizaciones_desde_editor(
            [
                {
                    "ars_por_usd": "1.200,000000",
                    "fuente": "MEP",
                    "lado": "=1+1",
                    "naturaleza": "OBSERVADA",
                    "referencia": "",
                }
            ],
            [cuota],
        )

def test_plantilla_indice_retorno_total_tiene_encabezados_documentados():
    contenido = _csv_plantilla_indice_retorno_total().decode("utf-8-sig")
    assert contenido.splitlines() == [
        "fecha;indice_retorno_total;moneda;tipo_indice;fuente;referencia"
    ]


def test_importar_serie_total_return_admite_coma_decimal_y_resumen_historico():
    contenido = (
        "\ufefffecha;indice_retorno_total;moneda;tipo_indice;fuente;referencia\n"
        "2025-01-01;100,000000;USD;BRUTO_TOTAL_RETURN;Proveedor índice total-return;metodología-v1\n"
        "2025-07-01;105,000000;USD;BRUTO_TOTAL_RETURN;Proveedor índice total-return;metodología-v1\n"
        "2026-01-01;110,000000;USD;BRUTO_TOTAL_RETURN;Proveedor índice total-return;metodología-v1\n"
    ).encode("utf-8")
    resumen, observaciones = _leer_csv_indice_retorno_total(contenido)
    assert len(observaciones) == 3
    assert observaciones[0].nivel_indice == Decimal("100.000000")
    assert observaciones[-1].referencia == "metodología-v1"
    assert resumen.moneda == "USD"
    assert resumen.fecha_inicio == date(2025, 1, 1)
    assert resumen.fecha_fin == date(2026, 1, 1)
    assert resumen.rendimiento_acumulado == Decimal("0.1")
    assert resumen.rendimiento_anualizado == Decimal("0.1")


@pytest.mark.parametrize(
    ("contenido", "mensaje"),
    [
        (
            b"fecha,indice_retorno_total,moneda,fuente,referencia\n",
            "Faltan columnas",
        ),
        (
            b"fecha;indice_retorno_total;moneda;tipo_indice;fuente;referencia\n"
            b"2025-01-01;100;USD;BRUTO_TOTAL_RETURN;Proveedor;ref1\n"
            b"2025-01-01;101;USD;BRUTO_TOTAL_RETURN;Proveedor;ref2\n",
            "no repetirse",
        ),
        (
            b"fecha;indice_retorno_total;moneda;tipo_indice;fuente;referencia\n"
            b"2025-01-01;100;USD;BRUTO_TOTAL_RETURN;Proveedor;ref1\n"
            b"2025-01-20;101;USD;BRUTO_TOTAL_RETURN;Proveedor;ref2\n",
            "al menos 30 días",
        ),
        (
            b"fecha;indice_retorno_total;moneda;tipo_indice;fuente;referencia\n"
            b"2025-01-01;100;USD;BRUTO_TOTAL_RETURN;Proveedor;ref1\n"
            b"2025-12-31;101;ARS;BRUTO_TOTAL_RETURN;Proveedor;ref2\n",
            "mezcla monedas",
        ),
        (
            b"fecha;indice_retorno_total;moneda;tipo_indice;fuente;referencia\n"
            b"2025-01-01;100;USD;BRUTO_TOTAL_RETURN;;ref1\n"
            b"2025-12-31;101;USD;BRUTO_TOTAL_RETURN;Proveedor;ref2\n",
            "fuente",
        ),
        (
            b"fecha;indice_retorno_total;moneda;tipo_indice;fuente;referencia\n"
            b"2025-01-01;100;USD;BRUTO_TOTAL_RETURN;Proveedor;ref1\n"
            b"2025-12-31;abc;USD;BRUTO_TOTAL_RETURN;Proveedor;ref2\n",
            "no es un número válido",
        ),
        (
            b"fecha;indice_retorno_total;moneda;tipo_indice;fuente;referencia\n"
            b"2025-01-01;100,12345678901;USD;BRUTO_TOTAL_RETURN;Proveedor;ref1\n"
            b"2025-12-31;101;USD;BRUTO_TOTAL_RETURN;Proveedor;ref2\n",
            "máximo 10 decimales",
        ),
        (
            b"fecha;indice_retorno_total;moneda;tipo_indice;fuente;referencia\n"
            b"2025-01-01;100;USD;PRECIO_SIMPLE;Proveedor;ref1\n"
            b"2025-12-31;101;USD;BRUTO_TOTAL_RETURN;Proveedor;ref2\n",
            "tipo de índice debe ser",
        ),
    ],
)
def test_importar_serie_total_return_rechaza_archivos_o_datos_invalidos(contenido, mensaje):
    with pytest.raises(ErrorValidacion, match=mensaje):
        _leer_csv_indice_retorno_total(contenido)


def test_importar_serie_total_return_rechaza_archivo_vacio_o_mal_codificado():
    with pytest.raises(ErrorValidacion, match="vacío"):
        _leer_csv_indice_retorno_total(b"")
    with pytest.raises(ErrorValidacion, match="UTF-8"):
        _leer_csv_indice_retorno_total(b"\xff\xfe\x00")


def test_csv_backtest_historico_exporta_fechas_desfase_xirr_y_procedencia_segura():
    resultado = SimpleNamespace(
        moneda="USD",
        tipo_indice="BRUTO_TOTAL_RETURN",
        cantidad_observaciones=3,
        capital_inicial_usd=Decimal("1000.00"),
        cantidad_flujos=2,
        fecha_inicio_operacion=date(2025, 1, 1),
        fecha_fin_operacion=date(2026, 1, 1),
        fecha_observacion_inicio=date(2025, 1, 1),
        fecha_observacion_fin=date(2026, 1, 1),
        dias_desfase_inicio=0,
        dias_desfase_fin=0,
        valor_final_capital_original=Decimal("1200.00"),
        valor_final_cuotas_reinvertidas=Decimal("627.27"),
        brecha_final=Decimal("-572.73"),
        rendimiento_anualizado_capital_original=Decimal("0.2"),
        xirr_cartera_reinvertida=None,
    )
    observaciones = (
        SimpleNamespace(fuente="=HYPERLINK(\"https://example.invalid\")", referencia="ref-1"),
        SimpleNamespace(fuente="Proveedor B", referencia="=2+2"),
    )
    contenido = _csv_backtest_indice_historico(
        resultado,
        benchmark="Índice USD",
        clase="Cartera / ETF",
        observaciones=observaciones,
    ).decode("utf-8-sig")
    assert "tipo_indice" in contenido.splitlines()[0]
    assert "BRUTO_TOTAL_RETURN" in contenido
    assert "'=HYPERLINK" in contenido
    assert "ref-1" in contenido
    assert "'=2+2" in contenido
    assert "1200.00" in contenido
    assert "-572.73" in contenido
    assert "xirr_cartera_reinvertida" in contenido
    assert "BACKTEST_HISTORICO" in contenido

def test_plantilla_precios_distribuciones_explicita_precio_no_ajustado_y_tipo():
    contenido = _csv_plantilla_precio_distribucion().decode("utf-8-sig")
    assert contenido.splitlines() == [
        "fecha;precio_no_ajustado;distribucion_por_unidad;moneda;"
        "tipo_indice;base_precio;fuente;referencia"
    ]


def test_importar_precios_distribuciones_deriva_indice_y_conserva_procedencia():
    contenido = (
        "\ufefffecha;precio_no_ajustado;distribucion_por_unidad;moneda;"
        "tipo_indice;base_precio;fuente;referencia\n"
        "2025-01-01;100,000000;0,000000;USD;BRUTO_TOTAL_RETURN;"
        "PRECIO_NO_AJUSTADO;Proveedor A;precio inicial\n"
        "2025-07-01;98,000000;3,000000;USD;BRUTO_TOTAL_RETURN;"
        "PRECIO_NO_AJUSTADO;Proveedor A;distribución julio\n"
        "2026-01-01;102,000000;2,000000;USD;BRUTO_TOTAL_RETURN;"
        "PRECIO_NO_AJUSTADO;Proveedor A;distribución enero\n"
    ).encode("utf-8")
    resumen, indice_derivado, precios = _leer_csv_precio_distribucion(contenido)
    assert len(precios) == len(indice_derivado) == 3
    assert indice_derivado[0].nivel_indice == Decimal("100.0000000000")
    assert indice_derivado[1].nivel_indice == Decimal("101.0000000000")
    assert indice_derivado[2].nivel_indice > indice_derivado[1].nivel_indice
    assert resumen.tipo_indice == "BRUTO_TOTAL_RETURN"
    assert resumen.moneda == "USD"
    assert "distribución por unidad reinvertida" in indice_derivado[1].referencia.lower()


@pytest.mark.parametrize(
    ("fila", "mensaje"),
    [
        (
            "2025-01-01;100;0;USD;BRUTO_TOTAL_RETURN;PRECIO_AJUSTADO;Prov;ref",
            "precio no ajustado",
        ),
        (
            "2025-01-01;100;1;USD;BRUTO_TOTAL_RETURN;PRECIO_NO_AJUSTADO;Prov;ref",
            "primera observación debe tener distribución cero",
        ),
        (
            "2025-01-01;100;0;USD;PRECIO_SIMPLE;PRECIO_NO_AJUSTADO;Prov;ref",
            "debe ser BRUTO_TOTAL_RETURN",
        ),
        (
            "2025-01-01;100;0;USD;BRUTO_TOTAL_RETURN;PRECIO_NO_AJUSTADO;;ref",
            "fuente",
        ),
    ],
)
def test_importar_precios_distribuciones_rechaza_doble_conteo_y_metadatos_invalidos(
    fila, mensaje
):
    cabecera = (
        "fecha;precio_no_ajustado;distribucion_por_unidad;moneda;"
        "tipo_indice;base_precio;fuente;referencia\n"
    )
    segunda = (
        "2026-01-01;101;0;USD;BRUTO_TOTAL_RETURN;"
        "PRECIO_NO_AJUSTADO;Prov;ref2\n"
    )
    with pytest.raises(ErrorValidacion, match=mensaje):
        _leer_csv_precio_distribucion((cabecera + fila + "\n" + segunda).encode("utf-8"))


def test_importar_precios_distribuciones_rechaza_precio_o_distribucion_mal_formados():
    cabecera = (
        "fecha;precio_no_ajustado;distribucion_por_unidad;moneda;"
        "tipo_indice;base_precio;fuente;referencia\n"
    )
    fila1 = (
        "2025-01-01;100;0;USD;BRUTO_TOTAL_RETURN;PRECIO_NO_AJUSTADO;Prov;ref\n"
    )
    with pytest.raises(ErrorValidacion, match="no es un número válido"):
        _leer_csv_precio_distribucion(
            (cabecera + fila1 + "2026-01-01;abc;1;USD;BRUTO_TOTAL_RETURN;"
             "PRECIO_NO_AJUSTADO;Prov;ref2\n").encode("utf-8")
        )
    with pytest.raises(ErrorValidacion, match="debe estar entre 0 y"):
        _leer_csv_precio_distribucion(
            (cabecera + fila1 + "2026-01-01;101;-1;USD;BRUTO_TOTAL_RETURN;"
             "PRECIO_NO_AJUSTADO;Prov;ref2\n").encode("utf-8")
        )



def test_csv_escenarios_benchmark_etiqueta_cagr_historico_y_exporta_procedencia():
    resultado = (
        SimpleNamespace(
            nombre="Base",
            tasa_anual_neta_usd=Decimal("0.08"),
            valor_capital_original_final_usd=Decimal("1080.00"),
            valor_cuotas_reinvertidas_final_usd=Decimal("1100.00"),
            brecha_final_usd=Decimal("20.00"),
        ),
    )
    resumen = SimpleNamespace(
        fecha_inicio=date(2024, 1, 1),
        fecha_fin=date(2026, 1, 1),
        moneda="USD",
        tipo_indice="BRUTO_TOTAL_RETURN",
        cantidad_observaciones=24,
        rendimiento_anualizado=Decimal("0.10"),
    )
    contenido = _csv_escenarios_benchmark(
        resultado,
        benchmark="Índice USD",
        clase="Cartera / ETF",
        tasas_brutas_pct={"Base": Decimal("10.0000")},
        costos_pct=Decimal("1.0000"),
        impuesto_pct=Decimal("20.0000"),
        origen_tasa_base="CAGR_HISTORICO_TOTAL_RETURN",
        resumen_historico=resumen,
        cagr_historico_usado=True,
        metodo_serie="PRECIO_NO_AJUSTADO_DISTRIBUCIONES_REINVERTIDAS_AL_CIERRE",
    ).decode("utf-8-sig")
    assert "CAGR_HISTORICO_TOTAL_RETURN" in contenido
    assert "2024-01-01" in contenido and "2026-01-01" in contenido
    assert "BRUTO_TOTAL_RETURN" in contenido
    assert "10.0" in contenido
    assert "true" in contenido
    assert "SENSIBILIDAD_CON_CAGR_HISTORICO" in contenido
    assert "historia_metodo_serie" in contenido.splitlines()[0]
    assert "PRECIO_NO_AJUSTADO_DISTRIBUCIONES_REINVERTIDAS_AL_CIERRE" in contenido


def test_csv_escenarios_benchmark_exporta_supuestos_y_escapa_metadatos():
    resultados = (
        SimpleNamespace(
            nombre="Conservador",
            tasa_anual_neta_usd=Decimal("0.012"),
            valor_capital_original_final_usd=Decimal("1012.00"),
            valor_cuotas_reinvertidas_final_usd=Decimal("1040.00"),
            brecha_final_usd=Decimal("28.00"),
        ),
        SimpleNamespace(
            nombre="Base",
            tasa_anual_neta_usd=Decimal("0.028"),
            valor_capital_original_final_usd=Decimal("1028.00"),
            valor_cuotas_reinvertidas_final_usd=Decimal("1060.00"),
            brecha_final_usd=Decimal("32.00"),
        ),
        SimpleNamespace(
            nombre="Alto",
            tasa_anual_neta_usd=Decimal("0.044"),
            valor_capital_original_final_usd=Decimal("1044.00"),
            valor_cuotas_reinvertidas_final_usd=Decimal("1080.00"),
            brecha_final_usd=Decimal("36.00"),
        ),
    )
    contenido = _csv_escenarios_benchmark(
        resultados,
        benchmark="=HYPERLINK(\"https://example.invalid\")",
        clase="Cartera / ETF",
        tasas_brutas_pct={
            "Conservador": Decimal("2.0000"),
            "Base": Decimal("4.0000"),
            "Alto": Decimal("6.0000"),
        },
        costos_pct=Decimal("0.5000"),
        impuesto_pct=Decimal("20.0000"),
    ).decode("utf-8-sig")
    encabezado, *filas = contenido.splitlines()
    assert "rendimiento_bruto_pct" in encabezado
    assert "costos_anuales_pct" in encabezado
    assert "impuesto_estimado_sobre_rendimiento_pct" in encabezado
    assert "rendimiento_neto_pct" in encabezado
    assert "naturaleza" in encabezado
    assert len(filas) == 3
    assert "'=HYPERLINK" in contenido
    assert "SENSIBILIDAD_SUPUESTO_MANUAL" in contenido
    assert "0.5000" in contenido and "20.0000" in contenido


def test_csv_unidad_usd_exporta_referencias_y_escapa_valores_formula():
    fecha_desembolso = date(2026, 1, 31)
    fecha_cuota = date(2026, 2, 28)
    cotizacion_inicial = CotizacionUnidad(
        fecha_cotizacion=fecha_desembolso,
        ars_por_usd=Decimal("1000.000000"),
        fuente="=1+1",
        lado="VENDEDOR",
        naturaleza="SUPUESTO",
        referencia="=2+2",
    )
    cotizacion_cuota = CotizacionUnidad(
        fecha_cotizacion=fecha_cuota,
        ars_por_usd=Decimal("1200.000000"),
        fuente="=3+3",
        lado="COMPRADOR",
        naturaleza="OBSERVADA",
        referencia="=4+4",
    )
    resultado = simular_unidad_usd(
        capital_desembolso_ars=Decimal("100000"),
        cotizacion_inicial=cotizacion_inicial,
        tasa_anual_usd=Decimal("0.04"),
        modalidad_tasa=ModalidadTasa.TEA,
        tasa_benchmark_usd=Decimal("0.04"),
        modalidad_benchmark=ModalidadTasa.TEA,
        convencion_dias=ConvencionDias.MENSUAL,
        sistema=SistemaAmortizacion.FRANCES,
        fecha_desembolso=fecha_desembolso,
        meses_carencia=0,
        plazo_amortizacion_meses=1,
        tratamiento_carencia=TratamientoCarencia.SIN_INTERES,
        modo_reposicion_interna=True,
        cotizaciones_por_vencimiento={fecha_cuota: cotizacion_cuota},
    )

    csv_resultado = _csv_unidad_usd(resultado).decode("utf-8-sig")
    assert "cotizacion_inicial_referencia" in csv_resultado.splitlines()[0]
    assert "referencia_cotizacion" in csv_resultado.splitlines()[0]
    assert "'=1+1" in csv_resultado
    assert "'=2+2" in csv_resultado
    assert "'=3+3" in csv_resultado
    assert "'=4+4" in csv_resultado

