"""Regresiones del cálculo directo de capacidad de pago."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from aplicacion.consultas.capacidad_pago_directa import (
    CobroFuturoDeclarado,
    CalidadDatoCobro,
    CuotaCronogramaCapacidad,
    EstadoCobroFuturo,
    FuenteCobroFuturo,
    evaluar_capacidad_pago_directa,
    evaluar_cronograma_capacidad_directa,
    evaluar_respaldo_liquidez_con_cobros_futuros,
)


def test_calcula_remanente_y_porcentaje_sobre_margen_declarado():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual=Decimal("250000"),
        cuota_nueva_mensual=Decimal("160000"),
        colchon_mensual=Decimal("20000"),
    )

    assert resultado.margen_libre_declarado == Decimal("250000.00")
    assert resultado.cuota_nueva_mensual == Decimal("160000.00")
    assert resultado.colchon_mensual == Decimal("20000.00")
    assert resultado.remanente_mensual == Decimal("70000.00")
    assert resultado.porcentaje_margen_comprometido == Decimal("64.00")


def test_el_margen_cero_o_negativo_se_conserva_y_no_calcula_porcentaje():
    cero = evaluar_capacidad_pago_directa(
        margen_libre_mensual=Decimal("0"),
        cuota_nueva_mensual=Decimal("10000"),
    )
    negativo = evaluar_capacidad_pago_directa(
        margen_libre_mensual=Decimal("-15000"),
        cuota_nueva_mensual=Decimal("10000"),
    )

    assert cero.remanente_mensual == Decimal("-10000.00")
    assert cero.porcentaje_margen_comprometido is None
    assert negativo.remanente_mensual == Decimal("-25000.00")
    assert negativo.porcentaje_margen_comprometido is None


def test_permita_cuota_mayor_que_margen_y_muestra_faltante():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual=Decimal("80000"),
        cuota_nueva_mensual=Decimal("100000"),
    )

    assert resultado.remanente_mensual == Decimal("-20000.00")
    assert resultado.porcentaje_margen_comprometido == Decimal("125.00")


@pytest.mark.parametrize("cuota", ["0", "-1", "NaN", "Infinity", "-Infinity"])
def test_rechaza_cuota_invalida(cuota):
    with pytest.raises(ValueError):
        evaluar_capacidad_pago_directa(
            margen_libre_mensual=Decimal("100000"),
            cuota_nueva_mensual=cuota,
        )


def test_rechaza_colchon_negativo():
    with pytest.raises(ValueError, match="colchón mensual"):
        evaluar_capacidad_pago_directa(
            margen_libre_mensual=Decimal("100000"),
            cuota_nueva_mensual=Decimal("20000"),
            colchon_mensual=Decimal("-1"),
        )


@pytest.mark.parametrize("margen", ["NaN", "Infinity", "-Infinity"])
def test_rechaza_margen_no_finito(margen):
    with pytest.raises(ValueError, match="margen libre"):
        evaluar_capacidad_pago_directa(
            margen_libre_mensual=margen,
            cuota_nueva_mensual=Decimal("20000"),
        )


def test_redondea_porcentaje_con_precision_explicita():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual=Decimal("3"),
        cuota_nueva_mensual=Decimal("1"),
    )

    assert resultado.porcentaje_margen_comprometido == Decimal("33.33")

def test_evalua_reserva_liquida_para_varios_meses_ajustados():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual="250000",
        cuota_nueva_mensual="160000",
        colchon_mensual="20000",
        reserva_liquida_disponible="180000",
        reserva_minima_protegida="30000",
        margen_libre_mes_ajustado="100000",
        meses_escenario_ajustado=2,
    )

    respaldo = resultado.respaldo_liquidez
    assert resultado.remanente_mensual == Decimal("70000.00")
    assert respaldo.reserva_utilizable == Decimal("150000.00")
    assert respaldo.remanente_mes_ajustado == Decimal("-80000.00")
    assert respaldo.faltante_mensual_escenario == Decimal("80000.00")
    assert respaldo.respaldo_requerido_escenario == Decimal("160000.00")
    assert respaldo.meses_completos_cubiertos == 1
    assert respaldo.respaldo_consumido_escenario == Decimal("150000.00")
    assert respaldo.respaldo_restante_escenario == Decimal("0.00")
    assert respaldo.faltante_no_cubierto_escenario == Decimal("10000.00")


def test_reserva_protegida_no_se_utiliza_y_puede_cubrir_el_escenario():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual="200000",
        cuota_nueva_mensual="100000",
        reserva_liquida_disponible="200000",
        reserva_minima_protegida="150000",
        margen_libre_mes_ajustado="80000",
        meses_escenario_ajustado=2,
    )

    respaldo = resultado.respaldo_liquidez
    assert respaldo.reserva_utilizable == Decimal("50000.00")
    assert respaldo.respaldo_requerido_escenario == Decimal("40000.00")
    assert respaldo.meses_completos_cubiertos == 2
    assert respaldo.respaldo_restante_escenario == Decimal("10000.00")
    assert respaldo.faltante_no_cubierto_escenario == Decimal("0.00")


def test_no_consumir_reserva_si_el_margen_ajustado_alcanza():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual="200000",
        cuota_nueva_mensual="100000",
        reserva_liquida_disponible="50000",
        margen_libre_mes_ajustado="120000",
        meses_escenario_ajustado=3,
    )

    respaldo = resultado.respaldo_liquidez
    assert respaldo.remanente_mes_ajustado == Decimal("20000.00")
    assert respaldo.respaldo_requerido_escenario == Decimal("0.00")
    assert respaldo.respaldo_consumido_escenario == Decimal("0.00")
    assert respaldo.respaldo_restante_escenario == Decimal("50000.00")
    assert respaldo.meses_completos_cubiertos == 3


def test_no_informa_cobertura_de_reserva_sin_escenario_ajustado():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual="200000",
        cuota_nueva_mensual="100000",
        reserva_liquida_disponible="50000",
    )

    respaldo = resultado.respaldo_liquidez
    assert respaldo.reserva_utilizable == Decimal("50000.00")
    assert respaldo.margen_libre_mes_ajustado is None
    assert respaldo.meses_completos_cubiertos is None
    assert respaldo.respaldo_consumido_escenario is None


def test_reserva_protegida_mayor_al_ahorro_deja_respaldo_utilizable_en_cero():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual="100000",
        cuota_nueva_mensual="20000",
        reserva_liquida_disponible="50000",
        reserva_minima_protegida="60000",
    )

    assert resultado.respaldo_liquidez.reserva_utilizable == Decimal("0.00")


@pytest.mark.parametrize("meses", [0, -1, 25, True, 1.5])
def test_rechaza_duracion_invalida_del_escenario_ajustado(meses):
    with pytest.raises(ValueError, match="duración del escenario"):
        evaluar_capacidad_pago_directa(
            margen_libre_mensual="100000",
            cuota_nueva_mensual="20000",
            margen_libre_mes_ajustado="50000",
            meses_escenario_ajustado=meses,
        )


def test_rechaza_margen_no_finito_en_escenario_ajustado():
    with pytest.raises(ValueError, match="mes ajustado"):
        evaluar_capacidad_pago_directa(
            margen_libre_mensual="100000",
            cuota_nueva_mensual="20000",
            margen_libre_mes_ajustado="NaN",
        )




def test_cobro_despues_del_primer_vencimiento_no_cubre_ese_mes():
    primer_vencimiento = date(2027, 1, 31)
    cobro = CobroFuturoDeclarado(
        importe="100000",
        fecha_prevista=primer_vencimiento + timedelta(days=1),
        origen="Venta de equipo",
    )

    resultado = evaluar_respaldo_liquidez_con_cobros_futuros(
        reserva_utilizable_inicial="0",
        faltante_mensual="100000",
        fecha_primer_vencimiento=primer_vencimiento,
        meses=2,
        cobros=[cobro],
        fecha_referencia=date(2027, 1, 1),
    )

    primero, segundo = resultado.periodos
    assert primero.cobros_esperados_hasta_vencimiento == Decimal("0.00")
    assert primero.faltante_no_cubierto == Decimal("100000.00")
    assert segundo.fecha_vencimiento == date(2027, 2, 28)
    assert segundo.cobros_esperados_hasta_vencimiento == Decimal("100000.00")
    assert segundo.faltante_no_cubierto == Decimal("0.00")
    assert resultado.meses_con_faltante == 1
    assert resultado.faltante_no_cubierto_total == Decimal("100000.00")
    assert resultado.saldo_respaldo_final == Decimal("0.00")


def test_reserva_cubre_primer_mes_y_cobro_futuro_repone_el_respaldo():
    primer_vencimiento = date(2027, 1, 31)
    cobro = CobroFuturoDeclarado(
        importe="100000",
        fecha_prevista=date(2027, 2, 15),
        origen="Trabajo facturado",
    )

    resultado = evaluar_respaldo_liquidez_con_cobros_futuros(
        reserva_utilizable_inicial="50000",
        faltante_mensual="50000",
        fecha_primer_vencimiento=primer_vencimiento,
        meses=2,
        cobros=[cobro],
        fecha_referencia=date(2027, 1, 1),
    )

    assert resultado.periodos[0].respaldo_al_cierre == Decimal("0.00")
    assert resultado.periodos[1].respaldo_al_cierre == Decimal("50000.00")
    assert resultado.faltante_no_cubierto_total == Decimal("0.00")
    assert resultado.total_cobros_en_escenario == Decimal("100000.00")


def test_demora_de_30_dias_puede_dejar_un_cobro_fuera_del_horizonte():
    primer_vencimiento = date(2027, 1, 31)
    cobro = CobroFuturoDeclarado(
        importe="120000",
        fecha_prevista=date(2027, 2, 1),
        origen="Factura a cobrar",
    )

    resultado = evaluar_respaldo_liquidez_con_cobros_futuros(
        reserva_utilizable_inicial="0",
        faltante_mensual="50000",
        fecha_primer_vencimiento=primer_vencimiento,
        meses=2,
        cobros=[cobro],
        demora_dias=30,
        fecha_referencia=date(2027, 1, 1),
    )

    assert resultado.total_cobros_en_escenario == Decimal("0.00")
    assert resultado.total_cobros_fuera_horizonte == Decimal("120000.00")
    assert resultado.faltante_no_cubierto_total == Decimal("100000.00")


def test_escenario_sin_cobros_no_incorpora_ninguna_entrada_futura():
    cobro = CobroFuturoDeclarado(
        importe="90000",
        fecha_prevista=date(2027, 2, 10),
        origen="Devolución pendiente",
    )

    resultado = evaluar_respaldo_liquidez_con_cobros_futuros(
        reserva_utilizable_inicial="10000",
        faltante_mensual="20000",
        fecha_primer_vencimiento=date(2027, 1, 31),
        meses=2,
        cobros=[cobro],
        demora_dias=None,
        fecha_referencia=date(2027, 1, 1),
    )

    assert resultado.total_cobros_en_escenario == Decimal("0.00")
    assert resultado.total_cobros_no_recibidos_escenario == Decimal("90000.00")
    assert resultado.faltante_no_cubierto_total == Decimal("30000.00")


def test_excluye_cobros_recibidos_cancelados_vencidos_o_incluidos_en_margen():
    referencia = date(2027, 1, 1)
    cobros = [
        CobroFuturoDeclarado(
            "1000", date(2027, 1, 10), "Cobro recibido", EstadoCobroFuturo.COBRADO
        ),
        CobroFuturoDeclarado(
            "2000", date(2027, 1, 10), "Cobro cancelado", EstadoCobroFuturo.CANCELADO
        ),
        CobroFuturoDeclarado("3000", date(2026, 12, 1), "Promesa vencida"),
        CobroFuturoDeclarado(
            "4000", date(2027, 2, 1), "Ya considerado en el margen",
            incluido_en_margen=True,
        ),
        CobroFuturoDeclarado("5000", date(2027, 2, 1), "Cobro adicional"),
    ]

    resultado = evaluar_respaldo_liquidez_con_cobros_futuros(
        reserva_utilizable_inicial="0",
        faltante_mensual="0",
        fecha_primer_vencimiento=date(2027, 1, 31),
        meses=2,
        cobros=cobros,
        fecha_referencia=referencia,
    )

    assert resultado.total_cobros_ya_recibidos_excluidos == Decimal("1000.00")
    assert resultado.total_cobros_cancelados_excluidos == Decimal("2000.00")
    assert resultado.total_cobros_vencidos_no_recibidos == Decimal("3000.00")
    assert resultado.total_cobros_incluidos_en_margen_excluidos == Decimal("4000.00")
    assert resultado.total_cobros_en_escenario == Decimal("5000.00")



def test_consolida_cobros_del_sistema_y_externos_sin_perder_el_origen():
    cobros = [
        CobroFuturoDeclarado(
            importe="100000",
            fecha_prevista=date(2027, 1, 20),
            origen="Préstamo PP-0001",
            fuente=FuenteCobroFuturo.SISTEMA_CONTRACTUAL,
            referencia="1:2027-01-20:COBRO_PROYECTADO",
            calidad=CalidadDatoCobro.SISTEMA_CONTRACTUAL,
        ),
        CobroFuturoDeclarado(
            importe="50000",
            fecha_prevista=date(2027, 2, 15),
            origen="Factura independiente",
        ),
    ]

    resultado = evaluar_respaldo_liquidez_con_cobros_futuros(
        reserva_utilizable_inicial="0",
        faltante_mensual="0",
        fecha_primer_vencimiento=date(2027, 1, 31),
        meses=2,
        cobros=cobros,
        fecha_referencia=date(2027, 1, 1),
    )

    assert resultado.total_cobros_en_escenario == Decimal("150000.00")
    assert resultado.total_cobros_sistema_en_escenario == Decimal("100000.00")
    assert resultado.total_cobros_externos_en_escenario == Decimal("50000.00")
    assert resultado.periodos[0].cobros_sistema_hasta_vencimiento == Decimal(
        "100000.00"
    )
    assert resultado.periodos[0].cobros_externos_hasta_vencimiento == Decimal(
        "0.00"
    )
    assert resultado.periodos[1].cobros_externos_hasta_vencimiento == Decimal(
        "50000.00"
    )


def test_no_duplica_una_referencia_de_cobro_contractual_del_sistema():
    cobro = CobroFuturoDeclarado(
        importe="100000",
        fecha_prevista=date(2027, 1, 20),
        origen="Préstamo PP-0001",
        fuente=FuenteCobroFuturo.SISTEMA_CONTRACTUAL,
        referencia="1:2027-01-20:COBRO_PROYECTADO",
        calidad=CalidadDatoCobro.SISTEMA_CONTRACTUAL,
    )

    with pytest.raises(ValueError, match="referencia.*no puede repetirse"):
        evaluar_respaldo_liquidez_con_cobros_futuros(
            reserva_utilizable_inicial="0",
            faltante_mensual="0",
            fecha_primer_vencimiento=date(2027, 1, 31),
            meses=1,
            cobros=[cobro, cobro],
            fecha_referencia=date(2027, 1, 1),
        )


def test_sin_cobros_distingue_vencidos_y_fuera_del_horizonte():
    cobros = [
        CobroFuturoDeclarado(
            importe="1000",
            fecha_prevista=date(2026, 12, 20),
            origen="Cobro vencido",
        ),
        CobroFuturoDeclarado(
            importe="2000",
            fecha_prevista=date(2027, 3, 1),
            origen="Cobro posterior al período",
        ),
        CobroFuturoDeclarado(
            importe="3000",
            fecha_prevista=date(2027, 2, 15),
            origen="Cobro previsto dentro del período",
        ),
    ]

    resultado = evaluar_respaldo_liquidez_con_cobros_futuros(
        reserva_utilizable_inicial="0",
        faltante_mensual="0",
        fecha_primer_vencimiento=date(2027, 1, 31),
        meses=2,
        cobros=cobros,
        demora_dias=None,
        fecha_referencia=date(2027, 1, 1),
    )

    assert resultado.total_cobros_vencidos_no_recibidos == Decimal("1000.00")
    assert resultado.total_cobros_fuera_horizonte == Decimal("2000.00")
    assert resultado.total_cobros_no_recibidos_escenario == Decimal("3000.00")
    assert resultado.total_cobros_en_escenario == Decimal("0.00")




def test_respaldo_con_faltantes_variables_respeta_fechas_de_cada_cuota():
    faltantes = [
        (date(2027, 1, 31), "20000"),
        (date(2027, 2, 28), "70000"),
        (date(2027, 3, 31), "0"),
    ]
    cobro = CobroFuturoDeclarado(
        importe="40000",
        fecha_prevista=date(2027, 2, 1),
        origen="Factura externa",
    )

    resultado = evaluar_respaldo_liquidez_con_cobros_futuros(
        reserva_utilizable_inicial="50000",
        faltante_mensual="0",
        fecha_primer_vencimiento=date(2027, 1, 31),
        meses=3,
        cobros=[cobro],
        fecha_referencia=date(2027, 1, 1),
        faltantes_por_vencimiento=faltantes,
    )

    assert [p.faltante_del_mes for p in resultado.periodos] == [
        Decimal("20000.00"),
        Decimal("70000.00"),
        Decimal("0.00"),
    ]
    assert resultado.periodos[0].respaldo_al_cierre == Decimal("30000.00")
    assert resultado.periodos[1].respaldo_al_cierre == Decimal("0.00")
    assert resultado.total_faltantes_requeridos == Decimal("90000.00")
    assert resultado.faltante_mensual_escenario == Decimal("70000.00")
    assert resultado.cantidad_periodos_evaluados == 3
    assert resultado.fecha_ultimo_vencimiento == date(2027, 3, 31)
    assert resultado.faltante_no_cubierto_total == Decimal("0.00")


def test_cronograma_completo_compara_cuotas_variables_y_respaldo_fechado():
    cronograma = [
        CuotaCronogramaCapacidad(1, date(2027, 1, 31), "110000"),
        CuotaCronogramaCapacidad(2, date(2027, 2, 28), "160000"),
        CuotaCronogramaCapacidad(3, date(2027, 3, 31), "90000"),
    ]
    cobros = [
        CobroFuturoDeclarado(
            importe="30000",
            fecha_prevista=date(2027, 2, 10),
            origen="Factura",
        )
    ]

    resultado = evaluar_cronograma_capacidad_directa(
        margen_libre_mensual="100000",
        colchon_mensual="10000",
        cronograma=cronograma,
        margen_libre_mes_ajustado="80000",
        reserva_liquida_disponible="50000",
        cobros_futuros=cobros,
        horizonte_respaldo_meses=2,
        fecha_referencia=date(2027, 1, 1),
    )

    assert resultado.cantidad_cuotas == 3
    assert resultado.total_cuotas == Decimal("360000.00")
    assert resultado.cuotas_con_faltante_habitual == 2
    assert resultado.cuotas_con_faltante_ajustado == 3
    assert resultado.peor_remanente_habitual == Decimal("-70000.00")
    assert resultado.peor_remanente_ajustado == Decimal("-90000.00")
    assert resultado.meses_respaldo_evaluados == 2
    assert [p.importe_cuota for p in resultado.periodos] == [
        Decimal("110000.00"),
        Decimal("160000.00"),
        Decimal("90000.00"),
    ]
    respaldo = resultado.proyeccion_respaldo
    assert respaldo is not None
    assert [p.fecha_vencimiento for p in respaldo.periodos] == [
        date(2027, 1, 31),
        date(2027, 2, 28),
    ]
    assert respaldo.total_faltantes_requeridos == Decimal("130000.00")
    assert respaldo.total_cobros_externos_en_escenario == Decimal("30000.00")
    assert respaldo.faltante_no_cubierto_total == Decimal("50000.00")
    assert respaldo.saldo_respaldo_final == Decimal("0.00")


def test_cronograma_sin_margen_estresado_compara_todo_el_plazo_sin_usar_reserva():
    resultado = evaluar_cronograma_capacidad_directa(
        margen_libre_mensual="120000",
        cronograma=[
            CuotaCronogramaCapacidad(1, date(2027, 1, 31), "100000"),
            CuotaCronogramaCapacidad(2, date(2027, 2, 28), "130000"),
        ],
        reserva_liquida_disponible="300000",
        fecha_referencia=date(2027, 1, 1),
    )

    assert resultado.cuotas_con_faltante_habitual == 1
    assert resultado.cuotas_con_faltante_ajustado is None
    assert resultado.proyeccion_respaldo is None


@pytest.mark.parametrize(
    "cronograma",
    [
        [
            CuotaCronogramaCapacidad(1, date(2027, 1, 31), "1000"),
            CuotaCronogramaCapacidad(2, date(2027, 1, 31), "1000"),
        ],
        [
            CuotaCronogramaCapacidad(1, date(2027, 2, 28), "1000"),
            CuotaCronogramaCapacidad(2, date(2027, 1, 31), "1000"),
        ],
        [CuotaCronogramaCapacidad(1, date(2026, 12, 31), "1000")],
    ],
)
def test_rechaza_cronogramas_con_fechas_duplicadas_desordenadas_o_pasadas(cronograma):
    with pytest.raises(ValueError):
        evaluar_cronograma_capacidad_directa(
            margen_libre_mensual="100000",
            cronograma=cronograma,
            fecha_referencia=date(2027, 1, 1),
        )


def test_rechaza_cuotas_no_numeradas_en_orden():
    with pytest.raises(ValueError, match="numerarse desde 1"):
        evaluar_cronograma_capacidad_directa(
            margen_libre_mensual="100000",
            cronograma=[
                CuotaCronogramaCapacidad(2, date(2027, 1, 31), "1000"),
            ],
            fecha_referencia=date(2027, 1, 1),
        )





def test_distingue_cobros_externos_declarados_y_con_referencia_documental():
    cobros = [
        CobroFuturoDeclarado(
            importe="20000",
            fecha_prevista=date(2027, 1, 15),
            origen="Trabajo independiente",
        ),
        CobroFuturoDeclarado(
            importe="30000",
            fecha_prevista=date(2027, 1, 20),
            origen="Factura F-2027-15",
            calidad=CalidadDatoCobro.REFERENCIA_DOCUMENTAL_DECLARADA,
            referencia_documental="Factura F-2027-15",
        ),
    ]

    resultado = evaluar_respaldo_liquidez_con_cobros_futuros(
        reserva_utilizable_inicial="0",
        faltante_mensual="0",
        fecha_primer_vencimiento=date(2027, 1, 31),
        meses=1,
        cobros=cobros,
        fecha_referencia=date(2027, 1, 1),
    )

    periodo = resultado.periodos[0]
    assert resultado.total_cobros_externos_en_escenario == Decimal("50000.00")
    assert resultado.total_cobros_externos_declarados_en_escenario == Decimal(
        "20000.00"
    )
    assert resultado.total_cobros_externos_referenciados_en_escenario == Decimal(
        "30000.00"
    )
    assert periodo.cobros_externos_declarados_hasta_vencimiento == Decimal(
        "20000.00"
    )
    assert periodo.cobros_externos_referenciados_hasta_vencimiento == Decimal(
        "30000.00"
    )


def test_rechaza_cobro_externo_con_calidad_documental_sin_referencia():
    cobro = CobroFuturoDeclarado(
        importe="10000",
        fecha_prevista=date(2027, 1, 15),
        origen="Factura",
        calidad=CalidadDatoCobro.REFERENCIA_DOCUMENTAL_DECLARADA,
    )

    with pytest.raises(
        ValueError,
        match="referencia documental declarada es obligatoria",
    ):
        evaluar_respaldo_liquidez_con_cobros_futuros(
            reserva_utilizable_inicial="0",
            faltante_mensual="0",
            fecha_primer_vencimiento=date(2027, 1, 31),
            meses=1,
            cobros=[cobro],
            fecha_referencia=date(2027, 1, 1),
        )


def test_cobro_contractual_del_sistema_conserva_fuente_y_calidad():
    cobro = CobroFuturoDeclarado(
        importe="10000",
        fecha_prevista=date(2027, 1, 15),
        origen="Préstamo PP-1",
        fuente=FuenteCobroFuturo.SISTEMA_CONTRACTUAL,
        referencia="1:2027-01-15:CUOTA",
        calidad=CalidadDatoCobro.SISTEMA_CONTRACTUAL,
    )

    resultado = evaluar_respaldo_liquidez_con_cobros_futuros(
        reserva_utilizable_inicial="0",
        faltante_mensual="0",
        fecha_primer_vencimiento=date(2027, 1, 31),
        meses=1,
        cobros=[cobro],
        fecha_referencia=date(2027, 1, 1),
    )

    assert resultado.total_cobros_sistema_en_escenario == Decimal("10000.00")
    assert resultado.total_cobros_externos_en_escenario == Decimal("0.00")


def test_evaluacion_directa_integra_cobros_sin_modificar_el_escenario_base():
    resultado = evaluar_capacidad_pago_directa(
        margen_libre_mensual="100000",
        cuota_nueva_mensual="150000",
        reserva_liquida_disponible="60000",
        reserva_minima_protegida="10000",
        margen_libre_mes_ajustado="100000",
        meses_escenario_ajustado=2,
        cobros_futuros=[
            CobroFuturoDeclarado(
                importe="100000",
                fecha_prevista=date(2027, 2, 15),
                origen="Trabajo independiente",
            )
        ],
        fecha_primer_vencimiento=date(2027, 1, 31),
        fecha_referencia=date(2027, 1, 1),
    )

    respaldo = resultado.respaldo_liquidez
    assert resultado.remanente_mensual == Decimal("-50000.00")
    assert respaldo.reserva_utilizable == Decimal("50000.00")
    assert respaldo.faltante_no_cubierto_escenario == Decimal("50000.00")
    assert respaldo.proyeccion_temporal is not None
    assert respaldo.proyeccion_temporal.faltante_no_cubierto_total == Decimal("0.00")


@pytest.mark.parametrize(
    ("cobros", "demora", "meses"),
    [
        ([], 15, 2),
        ([], False, 2),
        ([], 0, 0),
    ],
)
def test_rechaza_parametros_invalidos_de_cobros_futuros(cobros, demora, meses):
    with pytest.raises(ValueError):
        evaluar_respaldo_liquidez_con_cobros_futuros(
            reserva_utilizable_inicial="0",
            faltante_mensual="1000",
            fecha_primer_vencimiento=date(2027, 1, 31),
            meses=meses,
            cobros=cobros,
            demora_dias=demora,
            fecha_referencia=date(2027, 1, 1),
        )


def test_rechaza_cobro_futuro_con_importe_no_positivo_o_sin_origen():
    with pytest.raises(ValueError, match="mayor que cero"):
        evaluar_respaldo_liquidez_con_cobros_futuros(
            reserva_utilizable_inicial="0",
            faltante_mensual="1000",
            fecha_primer_vencimiento=date(2027, 1, 31),
            meses=1,
            cobros=[CobroFuturoDeclarado("0", date(2027, 2, 1), "Origen")],
            fecha_referencia=date(2027, 1, 1),
        )
    with pytest.raises(ValueError, match="origen"):
        evaluar_respaldo_liquidez_con_cobros_futuros(
            reserva_utilizable_inicial="0",
            faltante_mensual="1000",
            fecha_primer_vencimiento=date(2027, 1, 31),
            meses=1,
            cobros=[CobroFuturoDeclarado("1000", date(2027, 2, 1), "  ")],
            fecha_referencia=date(2027, 1, 1),
        )
