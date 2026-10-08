"""Regresiones de la consulta compartida de deuda del próximo pago."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.consultas.deuda_proximo_pago import ServicioDeudaProximoPago
from aplicacion.consultas.preview_pago import ServicioPreviewPago
from aplicacion.servicios import ServicioPagos, ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "deuda.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield db


@pytest.fixture
def prestamo(db):
    personas = PersonaRepo(db)
    deudor = personas.crear(nombre="Deudor", apellido="J17")
    inversor = personas.crear(nombre="Inversor", apellido="J17")
    return ServicioPrestamos(db).crear_completo(
        deudor_id=deudor,
        capital=Decimal("1000000"),
        plazo_meses=6,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[{"persona_id": inversor, "monto": Decimal("1000000")}],
        usuario="j17-test",
    )


def test_consulta_compartida_conserva_contrato_de_deuda(db, prestamo):
    servicio = ServicioDeudaProximoPago(db)

    deuda = servicio.calcular(prestamo, date(2026, 2, 1))

    assert deuda is not None
    assert deuda["cuota_objetivo"].estado == "PENDIENTE"
    assert deuda["cuota_interes"] > 0
    assert deuda["cuota_capital"] > 0
    assert deuda["total_a_pagar"] == (
        deuda["cuota_interes"]
        + deuda["cuota_capital"]
        + deuda["arrastre_interes"]
        + deuda["arrastre_capital"]
        + deuda["arrastre_mora"]
        + deuda["interes_extra"]
        + deuda["mora_nueva"]
    )


def test_preview_y_servicio_legacy_comparten_la_misma_lectura(db, prestamo):
    fecha = date(2026, 3, 15)

    deuda_compartida = ServicioDeudaProximoPago(db).calcular(prestamo, fecha)
    deuda_legacy = ServicioPagos(db).calcular_deuda_proximo_pago(prestamo, fecha)
    deuda_preview = ServicioPreviewPago(db).calcular_deuda_proximo_pago(
        prestamo, fecha
    )

    assert deuda_compartida == deuda_legacy == deuda_preview


def test_lectura_de_deuda_no_modifica_el_estado(db, prestamo):
    antes_pagos = db.consultar_uno("SELECT COUNT(*) AS n FROM pagos")["n"]
    antes_auditoria = db.consultar_uno("SELECT COUNT(*) AS n FROM auditoria")["n"]
    antes_ledger = db.consultar_uno("SELECT COUNT(*) AS n FROM ledger")["n"]

    deuda = ServicioDeudaProximoPago(db).calcular(
        prestamo,
        date(2026, 3, 15),
    )

    assert deuda is not None
    assert db.consultar_uno("SELECT COUNT(*) AS n FROM pagos")["n"] == antes_pagos
    assert (
        db.consultar_uno("SELECT COUNT(*) AS n FROM auditoria")["n"]
        == antes_auditoria
    )
    assert db.consultar_uno("SELECT COUNT(*) AS n FROM ledger")["n"] == antes_ledger
