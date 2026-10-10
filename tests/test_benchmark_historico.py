"""Pruebas del resumen de series históricas de retorno total."""
from datetime import date
from decimal import Decimal

import pytest

from dominio import (
    ErrorValidacion,
    ObservacionIndiceRetornoTotal,
    ObservacionPrecioDistribucion,
    derivar_indice_retorno_total_desde_precios,
    comparar_flujos_con_indice_historico,
    resumir_serie_indice_retorno_total,
    validar_serie_indice_retorno_total,
)


def _obs(
    fecha,
    nivel,
    *,
    moneda="USD",
    fuente="Fuente total-return A",
    tipo_indice="BRUTO_TOTAL_RETURN",
    referencia=None,
):
    return ObservacionIndiceRetornoTotal(
        fecha=fecha,
        nivel_indice=Decimal(str(nivel)),
        moneda=moneda,
        fuente=fuente,
        tipo_indice=tipo_indice,
        referencia=referencia,
    )


def test_resumen_serie_calcula_retorno_acumulado_anualizado_y_caida_maxima():
    serie = (
        _obs(date(2025, 1, 1), "100"),
        _obs(date(2025, 4, 1), "120", referencia="publicación / punto 2"),
        _obs(date(2025, 7, 1), "90"),
        _obs(date(2025, 12, 31), "110"),
    )
    resumen = resumir_serie_indice_retorno_total(serie)

    assert resumen.fecha_inicio == date(2025, 1, 1)
    assert resumen.fecha_fin == date(2025, 12, 31)
    assert resumen.dias_transcurridos == 364
    assert resumen.cantidad_observaciones == 4
    assert resumen.moneda == "USD"
    assert resumen.nivel_inicial == Decimal("100")
    assert resumen.nivel_final == Decimal("110")
    assert resumen.rendimiento_acumulado == Decimal("0.1")
    assert resumen.rendimiento_anualizado > Decimal("0.1")
    assert resumen.caida_maxima == Decimal("-0.25")


def test_serie_normaliza_moneda_y_metadatos_sin_perder_evidencia():
    observacion = _obs(
        date(2025, 1, 1),
        "100",
        moneda=" usd ",
        fuente="  Proveedor / índice total-return  ",
        referencia="  https://example.invalid/serie  ",
    )
    assert observacion.moneda == "USD"
    assert observacion.fuente == "Proveedor / índice total-return"
    assert observacion.referencia == "https://example.invalid/serie"


@pytest.mark.parametrize(
    "serie",
    [
        (),
        (_obs(date(2025, 1, 1), "100"),),
        (
            _obs(date(2025, 1, 1), "100"),
            _obs(date(2025, 1, 20), "101"),
        ),
        (
            _obs(date(2025, 2, 1), "101"),
            _obs(date(2025, 1, 1), "100"),
        ),
        (
            _obs(date(2025, 1, 1), "100"),
            _obs(date(2025, 1, 1), "101"),
        ),
        (
            _obs(date(2025, 1, 1), "100", moneda="USD"),
            _obs(date(2025, 3, 1), "101", moneda="ARS"),
        ),
    ],
)
def test_rechaza_series_incompletas_desordenadas_cortas_o_con_moneda_mixta(serie):
    with pytest.raises(ErrorValidacion):
        validar_serie_indice_retorno_total(serie)


@pytest.mark.parametrize(
    "nivel",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
        1000.0,
    ],
)
def test_observacion_rechaza_nivel_no_positivo_no_finito_o_float(nivel):
    with pytest.raises(ErrorValidacion):
        ObservacionIndiceRetornoTotal(
            fecha=date(2025, 1, 1),
            nivel_indice=nivel,
            moneda="USD",
            fuente="Índice",
            tipo_indice="BRUTO_TOTAL_RETURN",
        )


def test_rechaza_fuente_o_moneda_vacias():
    with pytest.raises(ErrorValidacion, match="moneda"):
        ObservacionIndiceRetornoTotal(
            fecha=date(2025, 1, 1), nivel_indice=Decimal("100"), moneda="", 
            fuente="Fuente", tipo_indice="BRUTO_TOTAL_RETURN"
        )
    with pytest.raises(ErrorValidacion, match="fuente"):
        ObservacionIndiceRetornoTotal(
            fecha=date(2025, 1, 1), nivel_indice=Decimal("100"), moneda="USD",
            fuente="", tipo_indice="BRUTO_TOTAL_RETURN"
        )


def test_serie_historica_rechaza_mezclar_indices_brutos_y_netos():
    with pytest.raises(ErrorValidacion, match="mezcla índices brutos/netos"):
        validar_serie_indice_retorno_total(
            (
                _obs(date(2025, 1, 1), "100", tipo_indice="BRUTO_TOTAL_RETURN"),
                _obs(
                    date(2025, 12, 31),
                    "110",
                    tipo_indice="NETO_TOTAL_RETURN",
                ),
            )
        )


def test_retorno_historico_puede_ser_negativo_y_no_se_pinta_como_ganancia():
    resumen = resumir_serie_indice_retorno_total(
        (
            _obs(date(2025, 1, 1), "100"),
            _obs(date(2025, 12, 31), "80"),
        )
    )
    assert resumen.rendimiento_acumulado == Decimal("-0.2")
    assert resumen.rendimiento_anualizado < Decimal("0")
    assert resumen.caida_maxima == Decimal("-0.2")

def _precio(
    fecha,
    precio,
    distribucion,
    *,
    moneda="USD",
    tipo_indice="BRUTO_TOTAL_RETURN",
    base_precio="PRECIO_NO_AJUSTADO",
    fuente="Fuente precio no ajustado",
    referencia=None,
):
    return ObservacionPrecioDistribucion(
        fecha=fecha,
        precio_no_ajustado=Decimal(str(precio)),
        distribucion_por_unidad=Decimal(str(distribucion)),
        moneda=moneda,
        tipo_indice=tipo_indice,
        base_precio=base_precio,
        fuente=fuente,
        referencia=referencia,
    )


def test_derivar_total_return_reinvierte_distribucion_en_el_cierre():
    serie = derivar_indice_retorno_total_desde_precios(
        (
            _precio(date(2025, 1, 1), "100", "0", referencia="precio base"),
            _precio(date(2025, 7, 1), "98", "3", referencia="distribución 3 por unidad"),
            _precio(date(2026, 1, 1), "102", "2", referencia="distribución 2 por unidad"),
        )
    )
    assert serie[0].nivel_indice == Decimal("100.0000000000")
    # 100 × (98 + 3) / 100 = 101: el dividendo compensa la caída del precio.
    assert serie[1].nivel_indice == Decimal("101.0000000000")
    assert serie[2].nivel_indice > serie[1].nivel_indice
    assert serie[2].tipo_indice == "BRUTO_TOTAL_RETURN"
    assert "distribución por unidad reinvertida" in serie[1].referencia


def test_derivar_total_return_sin_distribuciones_reproduce_el_indice_de_precio():
    serie = derivar_indice_retorno_total_desde_precios(
        (
            _precio(date(2025, 1, 1), "100", "0"),
            _precio(date(2025, 7, 1), "110", "0"),
        )
    )
    assert serie[0].nivel_indice == Decimal("100.0000000000")
    assert serie[1].nivel_indice == Decimal("110.0000000000")
    resumen = resumir_serie_indice_retorno_total(serie)
    assert resumen.rendimiento_acumulado == Decimal("0.1")


def test_derivar_total_return_preserva_clasificacion_neta_y_fuente():
    serie = derivar_indice_retorno_total_desde_precios(
        (
            _precio(
                date(2025, 1, 1), "100", "0",
                tipo_indice="NETO_TOTAL_RETURN", fuente="Proveedor neto"
            ),
            _precio(
                date(2025, 12, 31), "100", "5",
                tipo_indice="NETO_TOTAL_RETURN", fuente="Proveedor neto"
            ),
        )
    )
    assert serie[-1].nivel_indice == Decimal("105.0000000000")
    assert serie[-1].tipo_indice == "NETO_TOTAL_RETURN"
    assert serie[-1].fuente == "Proveedor neto"


def test_derivar_total_return_rechaza_precio_ajustado_para_evitar_doble_distribucion():
    with pytest.raises(ErrorValidacion, match="precio no ajustado"):
        _precio(
            date(2025, 1, 1),
            "100",
            "0",
            base_precio="PRECIO_AJUSTADO",
        )


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"distribucion": "-0.01"}, "no puede ser negativa"),
        ({"precio": "0"}, "precio no ajustado debe ser mayor a cero"),
        ({"precio": "NaN"}, "Decimal finito"),
        ({"precio": 100.0}, "Decimal finito"),
        ({"moneda": ""}, "moneda"),
        ({"fuente": ""}, "fuente"),
        ({"tipo_indice": "PRECIO_SIMPLE"}, "BRUTO_TOTAL_RETURN"),
    ],
)
def test_observacion_precio_distribucion_rechaza_datos_invalidos(cambios, mensaje):
    argumentos = {
        "fecha": date(2025, 1, 1),
        "precio": "100",
        "distribucion": "0",
    }
    argumentos.update(cambios)
    with pytest.raises(ErrorValidacion, match=mensaje):
        _precio(**argumentos)


def test_derivar_total_return_rechaza_distribucion_inicial_y_series_inconsistentes():
    with pytest.raises(ErrorValidacion, match="primera observación debe tener distribución cero"):
        derivar_indice_retorno_total_desde_precios(
            (
                _precio(date(2025, 1, 1), "100", "1"),
                _precio(date(2025, 7, 1), "100", "0"),
            )
        )
    with pytest.raises(ErrorValidacion, match="mezcla monedas"):
        derivar_indice_retorno_total_desde_precios(
            (
                _precio(date(2025, 1, 1), "100", "0"),
                _precio(date(2025, 7, 1), "100", "0", moneda="ARS"),
            )
        )
    with pytest.raises(ErrorValidacion, match="mezcla tratamientos bruto/neto"):
        derivar_indice_retorno_total_desde_precios(
            (
                _precio(date(2025, 1, 1), "100", "0"),
                _precio(date(2025, 7, 1), "100", "0", tipo_indice="NETO_TOTAL_RETURN"),
            )
        )


def test_backtest_reinvierte_cuotas_sobre_niveles_historicos_en_fechas_comunes():
    serie = (
        _obs(date(2025, 1, 1), "100"),
        _obs(date(2025, 7, 1), "110"),
        _obs(date(2026, 1, 1), "120"),
    )
    resultado = comparar_flujos_con_indice_historico(
        capital_inicial_usd=Decimal("1000.00"),
        fecha_desembolso=date(2025, 1, 1),
        flujos_cuotas=(
            (date(2025, 7, 1), Decimal("300.00")),
            (date(2026, 1, 1), Decimal("300.00")),
        ),
        observaciones=serie,
    )

    assert resultado.fecha_inicio_operacion == date(2025, 1, 1)
    assert resultado.fecha_fin_operacion == date(2026, 1, 1)
    assert resultado.moneda == "USD"
    assert resultado.tipo_indice == "BRUTO_TOTAL_RETURN"
    assert resultado.fecha_observacion_inicio == date(2025, 1, 1)
    assert resultado.fecha_observacion_fin == date(2026, 1, 1)
    assert resultado.valor_final_capital_original == Decimal("1200.00")
    assert resultado.valor_final_cuotas_reinvertidas == Decimal("627.27")
    assert resultado.brecha_final == Decimal("-572.73")
    assert resultado.rendimiento_anualizado_capital_original == Decimal("0.2")
    assert resultado.xirr_cartera_reinvertida is not None


def test_backtest_rechaza_fecha_fuera_de_cobertura_o_indice_no_usd():
    serie = (
        _obs(date(2025, 1, 1), "100"),
        _obs(date(2025, 7, 1), "110"),
        _obs(date(2026, 1, 1), "120"),
    )
    with pytest.raises(ErrorValidacion, match="fuera de la cobertura"):
        comparar_flujos_con_indice_historico(
            capital_inicial_usd=Decimal("1000"),
            fecha_desembolso=date(2024, 12, 1),
            flujos_cuotas=((date(2025, 7, 1), Decimal("300")),),
            observaciones=serie,
        )

    serie_ars = (
        _obs(date(2025, 1, 1), "100", moneda="ARS"),
        _obs(date(2025, 7, 1), "110", moneda="ARS"),
    )
    with pytest.raises(ErrorValidacion, match="requiere un índice expresado en USD"):
        comparar_flujos_con_indice_historico(
            capital_inicial_usd=Decimal("1000"),
            fecha_desembolso=date(2025, 1, 1),
            flujos_cuotas=((date(2025, 7, 1), Decimal("300")),),
            observaciones=serie_ars,
        )


def test_backtest_rechaza_cierre_obsoleto_y_flujos_fuera_de_historia():
    serie = (
        _obs(date(2025, 1, 1), "100"),
        _obs(date(2025, 4, 1), "105"),
        _obs(date(2026, 1, 1), "110"),
    )
    with pytest.raises(ErrorValidacion, match="dato obsoleto"):
        comparar_flujos_con_indice_historico(
            capital_inicial_usd=Decimal("1000"),
            fecha_desembolso=date(2025, 3, 15),
            flujos_cuotas=((date(2025, 4, 1), Decimal("300")),),
            observaciones=serie,
        )
    with pytest.raises(ErrorValidacion, match="fuera de la cobertura"):
        comparar_flujos_con_indice_historico(
            capital_inicial_usd=Decimal("1000"),
            fecha_desembolso=date(2025, 1, 1),
            flujos_cuotas=((date(2026, 2, 1), Decimal("300")),),
            observaciones=serie,
        )


@pytest.mark.parametrize("importe", [Decimal("0"), Decimal("-10"), Decimal("NaN"), 100.0])
def test_backtest_rechaza_importes_de_cuota_invalidos(importe):
    serie = (
        _obs(date(2025, 1, 1), "100"),
        _obs(date(2025, 7, 1), "110"),
    )
    with pytest.raises(ErrorValidacion, match="Decimal finito mayor a cero"):
        comparar_flujos_con_indice_historico(
            capital_inicial_usd=Decimal("1000"),
            fecha_desembolso=date(2025, 1, 1),
            flujos_cuotas=((date(2025, 7, 1), importe),),
            observaciones=serie,
        )


def test_backtest_usa_ultimo_cierre_previo_con_desfase_visible():
    serie = (
        _obs(date(2025, 1, 1), "100"),
        _obs(date(2025, 6, 30), "110"),
        _obs(date(2026, 1, 2), "119"),
        _obs(date(2026, 1, 5), "120"),
    )
    resultado = comparar_flujos_con_indice_historico(
        capital_inicial_usd=Decimal("1000"),
        fecha_desembolso=date(2025, 1, 2),
        flujos_cuotas=((date(2026, 1, 4), Decimal("300")),),
        observaciones=serie,
    )
    assert resultado.fecha_observacion_inicio == date(2025, 1, 1)
    assert resultado.dias_desfase_inicio == 1
    assert resultado.fecha_observacion_fin == date(2026, 1, 2)
    assert resultado.dias_desfase_fin == 2

