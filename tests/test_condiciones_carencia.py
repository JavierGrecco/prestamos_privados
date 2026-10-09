"""Pruebas del modelo inmutable de condiciones de carencia."""
from datetime import date
from decimal import Decimal

import pytest

from dominio import (
    ConvencionDias,
    ErrorValidacion,
    ModalidadTasa,
    SistemaAmortizacion,
    crear_condiciones_carencia,
    hash_snapshot,
    json_canonico,
    verificar_hash_snapshot,
)


def _crear(tratamiento="DIFERIR_SIMPLE_DISTRIBUIDO", **cambios):
    args = {
        "capital_original": Decimal("1000000.00"),
        "tasa_anual": Decimal("0.36"),
        "modalidad_tasa": ModalidadTasa.TNA,
        "convencion_dias": ConvencionDias.MENSUAL,
        "sistema": SistemaAmortizacion.FRANCES,
        "meses_carencia": 12,
        "fecha_desembolso": date(2026, 1, 31),
        "plazo_amortizacion_meses": 24,
        "tratamiento": tratamiento,
    }
    args.update(cambios)
    return crear_condiciones_carencia(**args)


def test_snapshot_calcula_fechas_importes_y_no_capitaliza_interes():
    condiciones = _crear()

    assert condiciones.fecha_fin_carencia == date(2027, 1, 31)
    assert condiciones.fecha_primer_vencimiento == date(2027, 2, 28)
    assert condiciones.interes_simple_referencia == Decimal("360000.00")
    assert condiciones.interes_carencia_debido == Decimal("360000.00")
    assert condiciones.interes_carencia_no_cobrado == Decimal("0.00")
    payload = condiciones.payload()
    assert payload["capital_original"] == "1000000.00"
    assert payload["tratamiento"] == "DIFERIR_SIMPLE_DISTRIBUIDO"
    assert payload["interes_carencia_debido"] == "360000.00"


def test_sin_interes_no_convierte_el_interes_de_referencia_en_deuda():
    condiciones = _crear("SIN_INTERES")

    assert condiciones.interes_simple_referencia == Decimal("360000.00")
    assert condiciones.interes_carencia_debido == Decimal("0.00")
    assert condiciones.interes_carencia_no_cobrado == Decimal("360000.00")


@pytest.mark.parametrize(
    "tratamiento",
    ["DIFERIR_SIMPLE_PRIMERA_CUOTA", "DIFERIR_SIMPLE_DISTRIBUIDO"],
)
def test_interes_diferido_simple_se_registra_como_componente_debido(tratamiento):
    condiciones = _crear(tratamiento)
    assert condiciones.interes_carencia_debido == condiciones.interes_simple_referencia
    assert condiciones.interes_carencia_no_cobrado == Decimal("0.00")


@pytest.mark.parametrize(
    "tratamiento",
    ["PAGAR_INTERES_DURANTE_CARENCIA", "CAPITALIZAR_AL_FIN", "CUALQUIERA"],
)
def test_tratamientos_que_aun_no_son_operativos_se_rechazan(tratamiento):
    with pytest.raises(ErrorValidacion, match="no está habilitado"):
        _crear(tratamiento)


@pytest.mark.parametrize(
    ("nombre", "valor", "mensaje"),
    [
        ("capital_original", Decimal("0"), "capital original"),
        ("tasa_anual", Decimal("-0.01"), "tasa anual"),
        ("meses_carencia", 0, "al menos un mes"),
        ("plazo_amortizacion_meses", 0, "plazo de amortización"),
    ],
)
def test_rechaza_condiciones_invalidas(nombre, valor, mensaje):
    with pytest.raises(ErrorValidacion, match=mensaje):
        _crear(**{nombre: valor})


def test_snapshot_json_y_hash_son_canonicos_y_verificables():
    condiciones = _crear()
    payload = condiciones.payload()
    json1 = json_canonico(payload)
    json2 = json_canonico(dict(reversed(list(payload.items()))))
    digest = hash_snapshot(json1)

    assert json1 == json2
    assert verificar_hash_snapshot(json1, digest)
    assert not verificar_hash_snapshot(json1 + " ", digest)
    assert not verificar_hash_snapshot("{no-json", digest)


def test_tea_actual365_se_refleja_en_el_snapshot_con_importe_no_capitalizado():
    condiciones = _crear(
        tasa_anual=Decimal("0.30"),
        modalidad_tasa=ModalidadTasa.TEA,
        convencion_dias=ConvencionDias.ACTUAL_365,
        fecha_desembolso=date(2026, 1, 1),
    )

    assert Decimal("250000.00") < condiciones.interes_carencia_debido < Decimal("300000.00")
    assert condiciones.interes_carencia_debido == condiciones.interes_simple_referencia
    assert condiciones.capital_original == Decimal("1000000.00")
