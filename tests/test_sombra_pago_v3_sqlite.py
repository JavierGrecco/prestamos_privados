"""I2 integration tests: real SQLite SOMBRA keeps Legacy effective."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.fabrica_sombra_pago_v3_sqlite import (
    crear_puente_sombra_pago_v3_sqlite,
)
from aplicacion.servicios.pagos import ServicioPagos
from aplicacion.servicios.sombra_pago_v3_sqlite import SombraPagoV3SQLite
from aplicacion.servicios.puente_motor_pago_v3 import (
    ModoMotorPagoV3,
    PuenteMotorPagoV3,
)
from dominio.excepciones import ErrorInvariante
from dominio.politica_pago import PoliticaImputacionPago
from dominio.tipos import ConceptoImputacion
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo
from infraestructura.repositorios.registro_pago_v3 import (
    RepositorioRegistroPagoSQLiteV3,
)
from aplicacion.servicios import ServicioPrestamos


def _crear_prestamo(db: BaseDatos) -> int:
    personas = PersonaRepo(db)
    deudor_id = personas.crear(nombre="Deudor", apellido="I2")
    inversor_id = personas.crear(nombre="Inversor", apellido="I2")
    return ServicioPrestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=Decimal("1000000"),
        plazo_meses=12,
        tasa_anual=Decimal("0.30"),
        modalidad_tasa="TNA",
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[{"persona_id": inversor_id, "monto": Decimal("1000000")}],
        usuario="i2",
        destino="SOMBRA SQLite",
    )


def _command(db: BaseDatos, prestamo_id: int) -> RegistrarPagoCommand:
    deuda = ServicioPagos(db).calcular_deuda_proximo_pago(
        prestamo_id=prestamo_id,
        fecha_calculo=date(2026, 2, 1),
    )
    assert deuda is not None
    return RegistrarPagoCommand(
        prestamo_id=prestamo_id,
        monto=deuda["total_a_pagar"],
        fecha_real=date(2026, 2, 1),
        fecha_valor=date(2026, 2, 1),
        usuario="i2",
        idempotency_key="I2-SOMBRA-001",
    )


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "i2.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        prestamo_id = _crear_prestamo(db)
        yield db, prestamo_id


def test_i2_sombra_sqlite_legacy_sigue_siendo_efectivo_y_v3_no_persiste(
    db,
):
    base, prestamo_id = db
    command = _command(base, prestamo_id)

    puente = crear_puente_sombra_pago_v3_sqlite(base)
    resultado = puente.ejecutar(command)

    assert resultado.modo is ModoMotorPagoV3.SOMBRA
    assert resultado.error_sombra is None
    assert resultado.divergencia is None
    assert isinstance(resultado.resultado_efectivo, int)
    assert resultado.plan_sombra_v3 is not None
    assert resultado.plan_sombra_v3.revision_prestamo == 0
    assert resultado.plan_sombra_v3.obligaciones_afectadas[0].estado_anterior == "PENDIENTE"
    assert base.consultar_uno(
        "SELECT COUNT(*) AS n FROM pagos WHERE prestamo_id = ?",
        (prestamo_id,),
    )["n"] == 1
    assert base.consultar_uno(
        "SELECT COUNT(*) AS n FROM pagos WHERE prestamo_id = ? AND motor_version LIKE 'V3%'",
        (prestamo_id,),
    )["n"] == 0

    assert base.consultar_uno(
        "SELECT COUNT(*) AS n FROM devengamientos WHERE prestamo_id = ?",
        (prestamo_id,),
    )["n"] == 0


def test_i2_el_plan_sombra_no_relee_estado_despues_de_legacy(db):
    base, prestamo_id = db
    command = _command(base, prestamo_id)

    repo = RepositorioRegistroPagoSQLiteV3(base)
    sombra = SombraPagoV3SQLite(repo)

    original = repo.obtener_estado_pago
    snapshots = []

    def capturar(command_):
        snapshot = original(command_.prestamo_id)
        snapshots.append(snapshot)
        return snapshot

    sombra.capturar_snapshot = capturar
    estados_recibidos_por_v3 = []

    def calcular_desde_snapshot(**kwargs):
        estados_recibidos_por_v3.append(
            kwargs["obligaciones"][0].estado
        )
        from dominio.motor_pagos_v3 import calcular_plan_pago
        return calcular_plan_pago(**kwargs)

    sombra._calculador = calcular_desde_snapshot

    def legacy(command_):
        return ServicioPagos(base).registrar_pago(
            prestamo_id=command_.prestamo_id,
            monto=command_.monto,
            fecha_real=command_.fecha_real,
            usuario=command_.usuario,
        )

    puente = PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.SOMBRA,
        registrar_legacy=legacy,
        capturar_snapshot=sombra.capturar_snapshot,
        planificar_v3_sombra=sombra.planificar,
        comparar_sombra=lambda pago_id, plan: None,
    )
    resultado = puente.ejecutar(command)

    assert len(snapshots) == 1
    assert snapshots[0].revision_prestamo == 0
    assert estados_recibidos_por_v3 == ["PENDIENTE"]
    assert resultado.plan_sombra_v3.revision_prestamo == 0

    fila_cuota = base.consultar_uno(
        "SELECT estado FROM cuotas ORDER BY id LIMIT 1"
    )
    assert fila_cuota["estado"] == "PAGADA"


def test_i2_error_del_calculo_v3_es_no_bloqueante_en_sqlite(db):
    base, prestamo_id = db
    command = _command(base, prestamo_id)

    repo = RepositorioRegistroPagoSQLiteV3(base)
    sombra = SombraPagoV3SQLite(
        repo,
        calculador_plan=lambda **kwargs: (_ for _ in ()).throw(
            ErrorInvariante("fallo V3 sombra I2")
        ),
    )

    legacy = ServicioPagos(base)

    puente = PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.SOMBRA,
        registrar_legacy=lambda c: legacy.registrar_pago(
            prestamo_id=c.prestamo_id,
            monto=c.monto,
            fecha_real=c.fecha_real,
            usuario=c.usuario,
        ),
        capturar_snapshot=sombra.capturar_snapshot,
        planificar_v3_sombra=sombra.planificar,
        comparar_sombra=lambda *_: None,
    )

    resultado = puente.ejecutar(command)

    assert isinstance(resultado.resultado_efectivo, int)
    assert resultado.plan_sombra_v3 is None
    assert resultado.error_sombra == "ErrorInvariante: fallo V3 sombra I2"
    assert base.consultar_uno(
        "SELECT COUNT(*) AS n FROM pagos WHERE prestamo_id = ?",
        (prestamo_id,),
    )["n"] == 1


def test_i3_divergencia_sombra_se_persiste_con_fingerprint_y_pago_legacy(db):
    base, prestamo_id = db
    command = _command(base, prestamo_id)

    puente = crear_puente_sombra_pago_v3_sqlite(
        base,
        comparador_sombra=lambda *_: "diferencia controlada I3",
    )
    resultado = puente.ejecutar(command)

    assert resultado.resultado_efectivo > 0
    assert resultado.divergencia is not None
    assert resultado.error_sombra is None

    observacion = base.consultar_uno(
        """SELECT prestamo_id, pago_legacy_id, fingerprint, tipo, resumen,
                  motor_version
           FROM observaciones_sombra_v3
           ORDER BY id DESC
           LIMIT 1"""
    )
    assert observacion is not None
    assert observacion["prestamo_id"] == prestamo_id
    assert observacion["pago_legacy_id"] == resultado.resultado_efectivo
    assert observacion["fingerprint"] == resultado.divergencia.fingerprint
    assert observacion["tipo"] == "DIVERGENCIA"
    assert observacion["resumen"] == "diferencia controlada I3"
    assert observacion["motor_version"] == "V3-SOMBRA"


def test_i3_error_sombra_se_persiste_sin_invalidar_legacy(db):
    base, prestamo_id = db
    command = _command(base, prestamo_id)

    def falla(**kwargs):
        raise ErrorInvariante("fallo controlado I3")

    puente = crear_puente_sombra_pago_v3_sqlite(
        base,
        calculador_plan=falla,
    )
    resultado = puente.ejecutar(command)

    assert resultado.resultado_efectivo > 0
    assert resultado.divergencia is None
    assert resultado.error_sombra == "ErrorInvariante: fallo controlado I3"

    observacion = base.consultar_uno(
        """SELECT prestamo_id, pago_legacy_id, tipo, resumen
           FROM observaciones_sombra_v3
           ORDER BY id DESC
           LIMIT 1"""
    )
    assert observacion is not None
    assert observacion["prestamo_id"] == prestamo_id
    assert observacion["pago_legacy_id"] == resultado.resultado_efectivo
    assert observacion["tipo"] == "ERROR_SOMBRA"
    assert observacion["resumen"] == "ErrorInvariante: fallo controlado I3"


def test_i3_fallo_de_persistencia_del_observer_no_bloquea_legacy(db):
    base, prestamo_id = db
    command = _command(base, prestamo_id)

    legado = ServicioPagos(base)

    def observer_falla(_):
        raise RuntimeError("observer fuera de servicio")

    puente = PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.SOMBRA,
        registrar_legacy=lambda c: legado.registrar_pago(
            prestamo_id=c.prestamo_id,
            monto=c.monto,
            fecha_real=c.fecha_real,
            usuario=c.usuario,
        ),
        capturar_snapshot=lambda c: RepositorioRegistroPagoSQLiteV3(
            base
        ).obtener_estado_pago(c.prestamo_id),
        planificar_v3_sombra=lambda c, snapshot: (
            __import__("dominio.motor_pagos_v3", fromlist=["calcular_plan_pago"])
            .calcular_plan_pago(
                prestamo_id=snapshot.prestamo_id,
                fecha_valor=c.fecha_valor,
                revision_prestamo=snapshot.revision_prestamo,
                monto_recibido=c.monto,
                obligaciones=tuple(snapshot.obligaciones),
            )
        ),
        comparar_sombra=lambda *_: "divergencia observer I3",
        observar_divergencia=observer_falla,
    )

    resultado = puente.ejecutar(command)

    assert resultado.resultado_efectivo > 0
    assert resultado.divergencia is not None
    assert resultado.error_observabilidad == "RuntimeError: observer fuera de servicio"
    assert base.consultar_uno(
        "SELECT COUNT(*) AS n FROM pagos WHERE prestamo_id = ?",
        (prestamo_id,),
    )["n"] == 1


def test_i18_sombra_resuelve_waterfall_desde_politica_vigente(db):
    base, prestamo_id = db

    PoliticaImputacionPagoRepo = __import__(
        "infraestructura.repositorios.politicas_pago",
        fromlist=["PoliticaPagoRepo"],
    ).PoliticaPagoRepo
    PoliticaImputacionPagoRepo(base).crear_version(
        prestamo_id,
        date(2026, 2, 1),
        PoliticaImputacionPago(
            orden_waterfall=(
                ConceptoImputacion.CAPITAL,
                ConceptoImputacion.INTERES,
                ConceptoImputacion.MORA,
            )
        ),
        usuario="i18",
    )

    command = RegistrarPagoCommand(
        prestamo_id=prestamo_id,
        monto=Decimal("5000.00"),
        fecha_real=date(2026, 2, 1),
        fecha_valor=date(2026, 2, 1),
        usuario="i18",
        idempotency_key="I18-SOMBRA-001",
    )

    puente = crear_puente_sombra_pago_v3_sqlite(
        base,
        comparador_sombra=lambda *_: None,
    )
    resultado = puente.ejecutar(command)

    assert resultado.error_sombra is None
    assert resultado.plan_sombra_v3 is not None
    assert [
        aplicacion.concepto
        for aplicacion in resultado.plan_sombra_v3.aplicaciones
    ] == [ConceptoImputacion.CAPITAL]
