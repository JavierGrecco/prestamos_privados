"""Caracterización del registrar_pago() actual.

Estas pruebas no intentan corregir el motor todavía. Documentan qué hace hoy
la operación para que podamos refactorizar después sin cambiar su resultado
por accidente.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.servicios import ServicioPagos, ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.excepciones import ErrorTransaccion
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import (
    AuditoriaRepo,
    LedgerRepo,
    PagoRepo,
    PersonaRepo,
    PrestamoRepo,
)


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "test.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield db


@pytest.fixture
def prestamo_activo(db):
    personas = PersonaRepo(db)
    deudor_id = personas.crear(nombre="Juan", apellido="Pérez")
    inversor_id = personas.crear(nombre="María", apellido="García")

    prestamo_id = ServicioPrestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=Decimal("1000000"),
        plazo_meses=12,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[{"persona_id": inversor_id, "monto": Decimal("1000000")}],
        usuario="admin",
    )
    return prestamo_id


def _cuotas(db, prestamo_id):
    repo = PrestamoRepo(db)
    version_id = repo.version_activa(prestamo_id)
    return repo.cuotas(version_id)


def _imputaciones(db, pago_id):
    return PagoRepo(db).imputaciones_de(pago_id)


def _total_imputado(db, pago_id):
    return sum((imp.monto for imp in _imputaciones(db, pago_id)), Decimal("0"))


def test_pago_exacto_conserva_el_total_y_cuadra_el_ledger(
    db, prestamo_activo
):
    servicio = ServicioPagos(db)
    deuda = servicio.calcular_deuda_proximo_pago(
        prestamo_activo, date(2026, 2, 1)
    )
    assert deuda is not None

    pago_id = servicio.registrar_pago(
        prestamo_id=prestamo_activo,
        monto=deuda["total_a_pagar"],
        fecha_real=date(2026, 2, 1),
        usuario="admin",
    )

    pago = PagoRepo(db).obtener(pago_id)
    assert pago is not None
    assert pago.estado == "VALIDA"
    assert _total_imputado(db, pago_id) == pago.monto_moneda_pago
    assert LedgerRepo(db).verificar_cuadre() is True


def test_pago_parcial_aplica_mora_interes_y_capital_en_orden(
    db, prestamo_activo
):
    servicio = ServicioPagos(db)
    fecha = date(2026, 2, 15)
    deuda = servicio.calcular_deuda_proximo_pago(prestamo_activo, fecha)
    assert deuda is not None
    assert deuda["mora_nueva"] > 0

    monto = deuda["mora_nueva"] + Decimal("1000.00")
    pago_id = servicio.registrar_pago(
        prestamo_id=prestamo_activo,
        monto=monto,
        fecha_real=fecha,
        usuario="admin",
    )

    imputaciones = {imp.concepto: imp.monto for imp in _imputaciones(db, pago_id)}
    assert imputaciones["MORA"] == deuda["mora_nueva"]
    assert imputaciones.get("INTERES", Decimal("0.00")) > 0
    assert imputaciones.get("CAPITAL", Decimal("0.00")) == Decimal("0.00")

    cuota = next(
        c for c in _cuotas(db, prestamo_activo)
        if c.id == deuda["cuota_objetivo"].id
    )
    assert cuota.estado == "PARCIAL"
    assert cuota.tuvo_pago_parcial is True


def test_pago_parcial_deja_capital_y_registra_interes_extra(
    db, prestamo_activo
):
    servicio = ServicioPagos(db)
    fecha = date(2026, 2, 1)
    deuda = servicio.calcular_deuda_proximo_pago(prestamo_activo, fecha)
    assert deuda is not None

    monto = (deuda["total_a_pagar"] / Decimal("2")).quantize(Decimal("0.01"))

    pago_id = servicio.registrar_pago(
        prestamo_id=prestamo_activo,
        monto=monto,
        fecha_real=fecha,
        usuario="admin",
    )

    pago = PagoRepo(db).obtener(pago_id)
    assert pago is not None
    assert pago.tipo_pago == "PARCIAL"
    assert pago.interes_extra_generado > 0

    cuota = next(
        c for c in _cuotas(db, prestamo_activo)
        if c.id == deuda["cuota_objetivo"].id
    )
    assert cuota.capital_pendiente > 0 or cuota.interes_pendiente > 0


def test_un_pago_completo_posterior_a_un_parcial_se_marca_como_complemento(
    db, prestamo_activo
):
    servicio = ServicioPagos(db)
    servicio.registrar_pago(
        prestamo_id=prestamo_activo,
        monto=Decimal("50000.00"),
        fecha_real=date(2026, 2, 1),
        usuario="admin",
    )

    fecha = date(2026, 3, 1)
    deuda = servicio.calcular_deuda_proximo_pago(prestamo_activo, fecha)
    assert deuda is not None

    pago_id = servicio.registrar_pago(
        prestamo_id=prestamo_activo,
        monto=deuda["total_a_pagar"],
        fecha_real=fecha,
        usuario="admin",
    )

    pago = PagoRepo(db).obtener(pago_id)
    assert pago is not None
    assert pago.tipo_pago == "COMPLEMENTO"


def test_excedente_sin_rai_o_rni_es_rechazado(db, prestamo_activo):
    servicio = ServicioPagos(db)
    deuda = servicio.calcular_deuda_proximo_pago(
        prestamo_activo, date(2026, 2, 1)
    )
    assert deuda is not None

    with pytest.raises(Exception) as exc:
        servicio.registrar_pago(
            prestamo_id=prestamo_activo,
            monto=deuda["total_a_pagar"] + Decimal("1000.00"),
            fecha_real=date(2026, 2, 1),
            usuario="admin",
        )

    assert "RAI" in str(exc.value)
    assert "RNI" in str(exc.value)


def test_adelanto_rai_registra_la_opcion_y_recalculo(
    db, prestamo_activo
):
    servicio = ServicioPagos(db)
    deuda = servicio.calcular_deuda_proximo_pago(
        prestamo_activo, date(2026, 2, 1)
    )
    assert deuda is not None

    pago_id = servicio.registrar_pago(
        prestamo_id=prestamo_activo,
        monto=deuda["total_a_pagar"] + Decimal("10000.00"),
        fecha_real=date(2026, 2, 1),
        usuario="admin",
        opcion_adelanto="RAI",
    )

    pago = PagoRepo(db).obtener(pago_id)
    assert pago is not None
    assert pago.tipo_pago == "ADELANTO_RAI"
    assert pago.opcion_adelanto == "RAI"
    assert pago.monto_a_capital == Decimal("10000.00")
    assert pago.cuotas_restantes_despues is not None


def test_adelanto_rni_registra_la_opcion_y_recalculo(
    db, prestamo_activo
):
    servicio = ServicioPagos(db)
    deuda = servicio.calcular_deuda_proximo_pago(
        prestamo_activo, date(2026, 2, 1)
    )
    assert deuda is not None

    pago_id = servicio.registrar_pago(
        prestamo_id=prestamo_activo,
        monto=deuda["total_a_pagar"] + Decimal("10000.00"),
        fecha_real=date(2026, 2, 1),
        usuario="admin",
        opcion_adelanto="RNI",
    )

    pago = PagoRepo(db).obtener(pago_id)
    assert pago is not None
    assert pago.tipo_pago == "ADELANTO_RNI"
    assert pago.opcion_adelanto == "RNI"
    assert pago.monto_a_capital == Decimal("10000.00")
    assert pago.cuotas_restantes_despues is not None


def test_pago_deja_auditoria_y_distribucion_a_inversores(
    db, prestamo_activo
):
    servicio = ServicioPagos(db)
    deuda = servicio.calcular_deuda_proximo_pago(
        prestamo_activo, date(2026, 2, 1)
    )
    assert deuda is not None

    pago_id = servicio.registrar_pago(
        prestamo_id=prestamo_activo,
        monto=deuda["total_a_pagar"],
        fecha_real=date(2026, 2, 1),
        usuario="auditor",
    )

    entradas = AuditoriaRepo(db).por_entidad("PAGO", pago_id)
    assert len(entradas) == 1
    assert entradas[0].operacion == "PAGO_REGISTRADO"
    assert entradas[0].usuario == "auditor"

    movimientos = LedgerRepo(db).por_entidad("PRESTAMO", prestamo_activo)
    assert any(m.tipo_movimiento == "PAGO_RECIBIDO" for m in movimientos)
    assert any(m.tipo_movimiento == "DISTRIBUCION_INVERSOR" for m in movimientos)
    assert LedgerRepo(db).verificar_cuadre() is True


def test_error_durante_ledger_revierte_pago_y_cambios_de_cuotas(
    db, prestamo_activo, monkeypatch
):
    servicio = ServicioPagos(db)
    deuda = servicio.calcular_deuda_proximo_pago(
        prestamo_activo, date(2026, 2, 1)
    )
    assert deuda is not None

    estado_antes = [
        (
            c.id,
            c.estado,
            c.interes_pendiente,
            c.capital_pendiente,
            c.mora_pendiente,
        )
        for c in _cuotas(db, prestamo_activo)
    ]
    pagos_antes = len(PagoRepo(db).por_prestamo(prestamo_activo))

    original = servicio.ledger.registrar_operacion
    llamadas = 0

    def fallar_en_la_segunda_operacion(*args, **kwargs):
        nonlocal llamadas
        llamadas += 1
        if llamadas == 2:
            raise RuntimeError("fallo provocado para probar rollback")
        return original(*args, **kwargs)

    monkeypatch.setattr(
        servicio.ledger,
        "registrar_operacion",
        fallar_en_la_segunda_operacion,
    )

    with pytest.raises(ErrorTransaccion) as exc:
        servicio.registrar_pago(
            prestamo_id=prestamo_activo,
            monto=deuda["total_a_pagar"],
            fecha_real=date(2026, 2, 1),
            usuario="admin",
        )

    # La capa de infraestructura traduce el error interno a ErrorTransaccion.
    # Conservamos la causa original para no perder el diagnóstico.
    assert "fallo provocado para probar rollback" in str(exc.value)
    assert isinstance(exc.value.__cause__, RuntimeError)

    assert len(PagoRepo(db).por_prestamo(prestamo_activo)) == pagos_antes
    estado_despues = [
        (
            c.id,
            c.estado,
            c.interes_pendiente,
            c.capital_pendiente,
            c.mora_pendiente,
        )
        for c in _cuotas(db, prestamo_activo)
    ]
    assert estado_despues == estado_antes
