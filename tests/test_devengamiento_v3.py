from datetime import date
from decimal import Decimal

import pytest

from dominio.devengamiento_v3 import (
    PoliticaInteres,
    calcular_dias,
    calcular_devengamiento_interes,
    calcular_fraccion_anual,
)
from dominio.excepciones import ErrorInvariante, ErrorValidacion
from dominio.tipos import ConvencionDias, ModalidadTasa


def politica(tasa="0.30", modalidad=ModalidadTasa.TNA, convencion=ConvencionDias.ACTUAL_365):
    return PoliticaInteres(
        tasa_anual=Decimal(tasa),
        modalidad_tasa=modalidad,
        convencion_dias=convencion,
    )


def test_tna_actual_365():
    d = calcular_devengamiento_interes(
        base=Decimal("10000"),
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 1, 31),
        politica=politica(),
        referencia="int-1",
    )
    assert d.dias == 30
    assert d.fraccion_anual == Decimal("30") / Decimal("365")
    assert d.monto == Decimal("246.58")
    assert d.referencia == "int-1"


def test_tna_actual_360():
    d = calcular_devengamiento_interes(
        base=Decimal("10000"),
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 1, 31),
        politica=politica(convencion=ConvencionDias.ACTUAL_360),
    )
    assert d.dias == 30
    assert d.monto == Decimal("250.00")


def test_tna_30e_360():
    d = calcular_devengamiento_interes(
        base=Decimal("10000"),
        fecha_desde=date(2026, 1, 15),
        fecha_hasta=date(2026, 2, 15),
        politica=politica(convencion=ConvencionDias.TREINTA_360),
    )
    assert d.dias == 30
    assert d.monto == Decimal("250.00")


def test_tea_mensual():
    d = calcular_devengamiento_interes(
        base=Decimal("10000"),
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 2, 1),
        politica=politica(
            modalidad=ModalidadTasa.TEA,
            convencion=ConvencionDias.MENSUAL,
        ),
    )
    assert d.dias == 30
    assert d.monto == Decimal("221.04")


def test_mensual_no_inventa_fraccion_para_quince_dias():
    with pytest.raises(ErrorValidacion):
        calcular_devengamiento_interes(
            base=Decimal("10000"),
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 16),
            politica=politica(convencion=ConvencionDias.MENSUAL),
        )


def test_mensual_acepta_cierres_de_mes():
    d = calcular_devengamiento_interes(
        base=Decimal("10000"),
        fecha_desde=date(2026, 1, 31),
        fecha_hasta=date(2026, 2, 28),
        politica=politica(convencion=ConvencionDias.MENSUAL),
    )
    assert d.monto == Decimal("250.00")


def test_actual_actual_cruza_anio_bisiesto():
    d = calcular_devengamiento_interes(
        base=Decimal("36600"),
        fecha_desde=date(2024, 12, 31),
        fecha_hasta=date(2025, 1, 2),
        politica=politica(convencion=ConvencionDias.ACTUAL_ACTUAL),
    )
    # 1 día de 2024 + 1 día de 2025, con su denominador correspondiente.
    esperado = (Decimal("1") / Decimal("366") + Decimal("1") / Decimal("365")) * Decimal("0.30") * Decimal("36600")
    assert d.dias == 2
    assert d.monto == esperado.quantize(Decimal("0.01"))


def test_periodo_cero_no_genera_interes():
    d = calcular_devengamiento_interes(
        base=Decimal("10000"),
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 1, 1),
        politica=politica(),
    )
    assert d.monto == Decimal("0.00")
    assert d.dias == 0


def test_base_negativa_rechazada():
    with pytest.raises(ErrorValidacion):
        calcular_devengamiento_interes(
            base=Decimal("-1"),
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 2, 1),
            politica=politica(),
        )


def test_tasa_negativa_rechazada():
    with pytest.raises(ErrorValidacion):
        politica(tasa="-0.01")


def test_fecha_invertida_rechazada():
    with pytest.raises(ErrorValidacion):
        calcular_devengamiento_interes(
            base=Decimal("10000"),
            fecha_desde=date(2026, 2, 1),
            fecha_hasta=date(2026, 1, 1),
            politica=politica(),
        )


def test_mismo_periodo_dias_y_fraccion_cero():
    desde = date(2026, 3, 10)
    hasta = date(2026, 3, 10)
    assert calcular_dias(desde, hasta, ConvencionDias.ACTUAL_365) == 0
    assert calcular_fraccion_anual(desde, hasta, ConvencionDias.ACTUAL_365) == Decimal("0")


def test_metadata_del_devengamiento_es_reproducible():
    p = politica(convencion=ConvencionDias.ACTUAL_365)
    d1 = calcular_devengamiento_interes(
        base=Decimal("15000"),
        fecha_desde=date(2026, 4, 1),
        fecha_hasta=date(2026, 4, 16),
        politica=p,
        referencia="cuota-7-interes",
    )
    d2 = calcular_devengamiento_interes(
        base=Decimal("15000"),
        fecha_desde=date(2026, 4, 1),
        fecha_hasta=date(2026, 4, 16),
        politica=p,
        referencia="cuota-7-interes",
    )
    assert d1 == d2
