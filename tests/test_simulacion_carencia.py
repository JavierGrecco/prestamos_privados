"""Regresiones del simulador puro de carencia y flujo de caja."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from ui.pagina_simulador_carencia import (
    _csv_calendario,
    _csv_comparacion,
    _cotizaciones_desde_editor,
    _csv_plantilla_cotizaciones,
    _leer_csv_cotizaciones,
    _parsear_decimal_es,
    _texto_csv_seguro,
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
    assert "1;2027-02-28;;VENDEDOR;SUPUESTO;" in plantilla
    assert "2;2027-03-31;;VENDEDOR;SUPUESTO;" in plantilla
    assert "3;2027-04-30;;VENDEDOR;SUPUESTO;" in plantilla


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

