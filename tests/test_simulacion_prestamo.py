"""Pruebas del servicio de simulación de nuevos préstamos."""

from datetime import date
from decimal import Decimal

from aplicacion.servicios.simulacion_prestamo import (
    ServicioSimulacionPrestamo,
)
from dominio import ConvencionDias, ModalidadTasa, SistemaAmortizacion


def test_cuota_inicial_usa_el_mismo_motor_de_amortizacion():
    servicio = ServicioSimulacionPrestamo()

    tabla = servicio.generar_tabla(
        capital=Decimal("100000"),
        tasa_anual=Decimal("0.24"),
        plazo_meses=12,
        modalidad_tasa=ModalidadTasa.TNA,
        sistema=SistemaAmortizacion.FRANCES,
        fecha_inicio=date(2026, 1, 31),
    )
    cuota = servicio.cuota_inicial(
        capital=Decimal("100000"),
        tasa_anual=Decimal("0.24"),
        plazo_meses=12,
        modalidad_tasa=ModalidadTasa.TNA,
        sistema=SistemaAmortizacion.FRANCES,
        fecha_inicio=date(2026, 1, 31),
    )

    assert cuota == tabla[0]["cuota"]
    assert len(tabla) == 12
    assert tabla[-1]["saldo"] == Decimal("0.00")


def test_interes_primer_periodo_usa_la_fecha_real_y_la_convencion():
    servicio = ServicioSimulacionPrestamo()

    interes = servicio.interes_primer_periodo(
        capital=Decimal("100000"),
        tasa_anual=Decimal("0.24"),
        modalidad_tasa=ModalidadTasa.TNA,
        convencion_dias=ConvencionDias.ACTUAL_365,
        fecha_inicio=date(2026, 1, 31),
    )

    # 31/01/2026 -> 28/02/2026 = 28 días.
    assert interes == Decimal("184.11")


def test_comparacion_convenciones_no_usa_un_31_fijo():
    servicio = ServicioSimulacionPrestamo()
    resultado = servicio.comparar_convenciones_primer_periodo(
        capital=Decimal("100000"),
        tasa_anual=Decimal("0.24"),
        modalidad_tasa=ModalidadTasa.TNA,
        fecha_inicio=date(2026, 1, 31),
    )

    assert resultado[ConvencionDias.ACTUAL_365] == Decimal("184.11")
    assert resultado[ConvencionDias.ACTUAL_360] == Decimal("186.67")
    assert resultado[ConvencionDias.TREINTA_360] == Decimal("200.00")
    assert resultado[ConvencionDias.MENSUAL] == Decimal("2000.00")


def test_comparar_tasas_devuelve_ambas_modalidades():
    servicio = ServicioSimulacionPrestamo()

    resultado = servicio.comparar_tasas(
        capital=Decimal("100000"),
        tasa_anual=Decimal("0.24"),
        plazo_meses=12,
        sistema=SistemaAmortizacion.FRANCES,
        fecha_inicio=date(2026, 1, 1),
    )

    assert resultado.tna is not None
    assert resultado.tea is not None
