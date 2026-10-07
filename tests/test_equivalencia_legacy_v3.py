from datetime import date
from decimal import Decimal
import shutil

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios import ServicioPagos, ServicioPrestamos
from aplicacion.servicios.fabrica_registro_pago_v3 import crear_registrador_pago_v3_completo
from dominio.tipos import ConvencionDias, ModalidadTasa
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo, PrestamoRepo

from tests.equivalencia.comparador_pagos import comparar_pagos, proyectar_pago


def _crear_estado_base(path, *, seed_only: bool = False):
    db = BaseDatos(path)
    db.abrir()
    aplicar_migraciones(db)

    personas = PersonaRepo(db)
    deudor = personas.crear(nombre="Deudor H1", apellido="Prueba")
    inversor_a = personas.crear(nombre="Inversor A", apellido="H1")
    inversor_b = personas.crear(nombre="Inversor B", apellido="H1")

    prestamo_id = ServicioPrestamos(db).crear_completo(
        deudor_id=deudor,
        capital=Decimal("1000000"),
        plazo_meses=12,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[
            {"persona_id": inversor_a, "monto": Decimal("600000")},
            {"persona_id": inversor_b, "monto": Decimal("400000")},
        ],
        usuario="h1",
        destino="Escenario H1",
    )
    db.cerrar()
    return prestamo_id


@pytest.fixture
def estados_equivalentes(tmp_path):
    semilla = tmp_path / "seed.db"
    _crear_estado_base(semilla)
    legacy_path = tmp_path / "legacy.db"
    v3_path = tmp_path / "v3.db"
    shutil.copy2(semilla, legacy_path)
    shutil.copy2(semilla, v3_path)

    legacy = BaseDatos(legacy_path)
    v3 = BaseDatos(v3_path)
    legacy.abrir()
    v3.abrir()
    try:
        yield legacy, v3
    finally:
        legacy.cerrar()
        v3.cerrar()


def test_h1_001_pago_exacto_en_vencimiento_es_economicamente_equivalente(
    estados_equivalentes,
):
    legacy_db, v3_db = estados_equivalentes

    prestamo_id = 1
    legacy = ServicioPagos(legacy_db)
    deuda = legacy.calcular_deuda_proximo_pago(
        prestamo_id=prestamo_id,
        fecha_calculo=date(2026, 2, 1),
    )
    assert deuda is not None

    monto = deuda["total_a_pagar"]
    command = RegistrarPagoCommand(
        prestamo_id=prestamo_id,
        monto=monto,
        fecha_real=date(2026, 2, 1),
        fecha_valor=date(2026, 2, 1),
        usuario="h1",
        idempotency_key="H1-001",
    )

    pago_legacy = legacy.registrar_pago(
        prestamo_id=command.prestamo_id,
        monto=command.monto,
        fecha_real=command.fecha_real,
        usuario=command.usuario,
    )

    v3 = crear_registrador_pago_v3_completo(
        v3_db,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa=ModalidadTasa.TNA,
        convencion_dias=ConvencionDias.ACTUAL_365,
    )
    resultado_v3 = v3.ejecutar(command)

    esperado = proyectar_pago(legacy_db, pago_legacy)
    obtenido = proyectar_pago(v3_db, resultado_v3.pago_id)

    comparacion = comparar_pagos(esperado, obtenido)

    assert comparacion.ok, comparacion.diferencias
