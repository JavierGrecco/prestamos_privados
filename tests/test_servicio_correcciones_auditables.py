"""Pruebas del servicio de propuestas de corrección auditable."""

from datetime import date, datetime, timedelta
import hashlib
from decimal import Decimal, ROUND_HALF_UP
import json

import pytest

from aplicacion.servicios import ServicioCorreccionesAuditables
from dominio.excepciones import ErrorValidacion
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.excepciones import ErrorTransaccion
from infraestructura.repositorios import PlanesReposicionRepo


@pytest.fixture
def caso_aporte(tmp_path):
    with BaseDatos(tmp_path / "correcciones.db") as db:
        aplicar_migraciones(db)
        planes = PlanesReposicionRepo(db)
        plan_id, _ = planes.crear_plan_con_snapshot(
            nombre="Plan de prueba",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date.today() - timedelta(days=30),
            capital_original_ars=Decimal("10000.00"),
            datos={"objetivo": "prueba de correcciones"},
            creado_por="admin",
        )
        aporte_id = planes.registrar_aporte(
            plan_id,
            fecha_aporte=date.today() - timedelta(days=1),
            monto_ars=Decimal("1000.00"),
            cotizacion_ars_por_usd=Decimal("1000.000000"),
            naturaleza_cotizacion="SUPUESTO",
            fuente_cotizacion="",
            referencia="aporte de prueba",
            nota="",
            creado_por="admin",
        )
        aporte = planes.obtener_aporte(aporte_id)
        assert aporte is not None and aporte.snapshot_json is not None
        yield db, planes, aporte


def _snapshot_corregido(aporte, monto: str) -> dict:
    datos = json.loads(aporte.snapshot_json)
    importe = Decimal(monto)
    cotizacion = Decimal(datos["cotizacion_ars_por_usd"])
    datos["monto_ars"] = monto
    datos["equivalente_usd"] = format(
        (importe / cotizacion).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "f",
    )
    return datos


def _registrar(servicio, aporte, snapshot, *, clave="correccion-0001", anterior=None):
    return servicio.registrar_propuesta(
        entidad_tipo="APORTE_REPOSICION",
        entidad_id=aporte.id,
        hash_original=aporte.snapshot_sha256,
        snapshot_corregido=snapshot,
        motivo="El importe se había cargado incorrectamente",
        corregido_por="admin",
        clave_idempotencia=clave,
        correccion_anterior_id=anterior,
    )


def test_registra_propuesta_con_hashes_y_trazabilidad(caso_aporte):
    db, planes, aporte = caso_aporte
    servicio = ServicioCorreccionesAuditables(db)
    propuesta = _registrar(servicio, aporte, _snapshot_corregido(aporte, "1200.00"))

    assert propuesta.id > 0
    assert propuesta.entidad_tipo == "APORTE_REPOSICION"
    assert propuesta.entidad_id == aporte.id
    assert propuesta.hash_original == aporte.snapshot_sha256
    assert len(propuesta.hash_corregido) == 64
    assert propuesta.hash_corregido == hashlib.sha256(
        propuesta.snapshot_corregido_json.encode("utf-8")
    ).hexdigest()
    timestamp = datetime.fromisoformat(propuesta.corregido_en_utc)
    assert timestamp.tzinfo is not None and timestamp.utcoffset() == timedelta(0)
    assert propuesta.corregido_por == "admin"
    assert propuesta.clave_idempotencia == "correccion-0001"
    assert propuesta.correccion_anterior_id is None

    payload = json.loads(propuesta.snapshot_corregido_json)
    assert payload["monto_ars"] == "1200.00"

    original_persistido = planes.obtener_aporte(aporte.id)
    assert original_persistido is not None
    assert original_persistido.snapshot_json == aporte.snapshot_json
    assert original_persistido.snapshot_sha256 == aporte.snapshot_sha256


def test_reintento_idempotente_devuelve_la_misma_correccion(caso_aporte):
    db, _, aporte = caso_aporte
    servicio = ServicioCorreccionesAuditables(db)
    snapshot = _snapshot_corregido(aporte, "1200.00")

    primera = _registrar(servicio, aporte, snapshot)
    reintento = _registrar(servicio, aporte, snapshot)

    assert reintento.id == primera.id
    assert len(servicio.listar_historial(
        entidad_tipo="APORTE_REPOSICION", entidad_id=aporte.id
    )) == 1


def test_reutilizar_clave_con_otra_solicitud_es_rechazado(caso_aporte):
    db, _, aporte = caso_aporte
    servicio = ServicioCorreccionesAuditables(db)
    _registrar(servicio, aporte, _snapshot_corregido(aporte, "1200.00"))

    with pytest.raises(ErrorValidacion, match="solicitud diferente"):
        servicio.registrar_propuesta(
            entidad_tipo="APORTE_REPOSICION",
            entidad_id=aporte.id,
            hash_original=aporte.snapshot_sha256,
            snapshot_corregido=_snapshot_corregido(aporte, "1300.00"),
            motivo="El importe se había cargado incorrectamente",
            corregido_por="admin",
            clave_idempotencia="correccion-0001",
        )


def test_rechaza_hash_original_desactualizado_sin_persistir(caso_aporte):
    db, _, aporte = caso_aporte
    servicio = ServicioCorreccionesAuditables(db)
    with pytest.raises(ErrorValidacion, match="desactualizado"):
        servicio.registrar_propuesta(
            entidad_tipo="APORTE_REPOSICION",
            entidad_id=aporte.id,
            hash_original="f" * 64,
            snapshot_corregido=_snapshot_corregido(aporte, "1200.00"),
            motivo="El importe se había cargado incorrectamente",
            corregido_por="admin",
            clave_idempotencia="correccion-0002",
        )
    assert servicio.listar_historial(
        entidad_tipo="APORTE_REPOSICION", entidad_id=aporte.id
    ) == ()


def test_rechaza_float_y_campos_financieros_incoherentes(caso_aporte):
    db, _, aporte = caso_aporte
    servicio = ServicioCorreccionesAuditables(db)
    snapshot_float = _snapshot_corregido(aporte, "1200.00")
    snapshot_float["monto_ars"] = 1200.0
    with pytest.raises(ErrorValidacion, match="no admite float"):
        _registrar(servicio, aporte, snapshot_float)

    snapshot_incoherente = _snapshot_corregido(aporte, "1200.00")
    snapshot_incoherente["equivalente_usd"] = "1.00"
    with pytest.raises(ErrorValidacion, match="equivalente USD"):
        _registrar(servicio, aporte, snapshot_incoherente, clave="correccion-0002")

    assert servicio.listar_historial(
        entidad_tipo="APORTE_REPOSICION", entidad_id=aporte.id
    ) == ()


def test_correcciones_sucesivas_deben_encadenarse(caso_aporte):
    db, _, aporte = caso_aporte
    servicio = ServicioCorreccionesAuditables(db)
    primera = _registrar(servicio, aporte, _snapshot_corregido(aporte, "1200.00"))
    snapshot_segundo = json.loads(primera.snapshot_corregido_json)
    snapshot_segundo["monto_ars"] = "1300.00"
    snapshot_segundo["equivalente_usd"] = "1.30"

    with pytest.raises(ErrorValidacion, match="corrección anterior"):
        servicio.registrar_propuesta(
            entidad_tipo="APORTE_REPOSICION",
            entidad_id=aporte.id,
            hash_original=aporte.snapshot_sha256,
            snapshot_corregido=snapshot_segundo,
            motivo="Ajuste adicional del importe",
            corregido_por="admin",
            clave_idempotencia="correccion-0002",
        )

    segunda = servicio.registrar_propuesta(
        entidad_tipo="APORTE_REPOSICION",
        entidad_id=aporte.id,
        hash_original=aporte.snapshot_sha256,
        snapshot_corregido=snapshot_segundo,
        motivo="Ajuste adicional del importe",
        corregido_por="admin",
        clave_idempotencia="correccion-0002",
        correccion_anterior_id=primera.id,
    )
    historial = servicio.listar_historial(
        entidad_tipo="APORTE_REPOSICION", entidad_id=aporte.id
    )
    assert [item.id for item in historial] == [primera.id, segunda.id]
    assert segunda.correccion_anterior_id == primera.id


def test_no_permite_alterar_identidad_o_trazabilidad_del_original(caso_aporte):
    db, _, aporte = caso_aporte
    servicio = ServicioCorreccionesAuditables(db)
    snapshot = _snapshot_corregido(aporte, "1200.00")
    snapshot["plan_id"] = int(snapshot["plan_id"]) + 1

    with pytest.raises(ErrorValidacion, match="plan_id"):
        _registrar(servicio, aporte, snapshot)
    assert servicio.listar_historial(
        entidad_tipo="APORTE_REPOSICION", entidad_id=aporte.id
    ) == ()


def test_rechaza_entidad_y_referencias_invalidas(caso_aporte):
    db, _, aporte = caso_aporte
    servicio = ServicioCorreccionesAuditables(db)
    snapshot = _snapshot_corregido(aporte, "1200.00")
    with pytest.raises(ErrorValidacion, match="tipo de entidad"):
        servicio.registrar_propuesta(
            entidad_tipo="PRESTAMO",
            entidad_id=aporte.id,
            hash_original=aporte.snapshot_sha256,
            snapshot_corregido=snapshot,
            motivo="Motivo válido",
            corregido_por="admin",
            clave_idempotencia="correccion-0003",
        )

    with pytest.raises(ErrorValidacion, match="No existe una corrección previa"):
        servicio.registrar_propuesta(
            entidad_tipo="APORTE_REPOSICION",
            entidad_id=aporte.id,
            hash_original=aporte.snapshot_sha256,
            snapshot_corregido=snapshot,
            motivo="Motivo válido",
            corregido_por="admin",
            clave_idempotencia="correccion-0004",
            correccion_anterior_id=999,
        )



@pytest.fixture
def caso_inversion(tmp_path):
    with BaseDatos(tmp_path / "correcciones_inversion.db") as db:
        aplicar_migraciones(db)
        planes = PlanesReposicionRepo(db)
        plan_id, _ = planes.crear_plan_con_snapshot(
            nombre="Cartera para corregir",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date.today() - timedelta(days=90),
            capital_original_ars=Decimal("10000.00"),
            datos={"objetivo": "prueba de correcciones de inversión"},
            creado_por="admin",
        )
        flujo_id = planes.registrar_flujo_inversion(
            plan_id,
            fecha_flujo=date.today() - timedelta(days=30),
            tipo_flujo="APORTE_INVERSION",
            moneda="USD",
            monto_original=Decimal("1000.00"),
            naturaleza_cotizacion="NO_APLICA",
            creado_por="admin",
        )
        valoracion_id = planes.registrar_valoracion_inversion(
            plan_id,
            fecha_valuacion=date.today(),
            moneda="USD",
            valor_original=Decimal("1100.00"),
            naturaleza_cotizacion="NO_APLICA",
            creado_por="admin",
        )
        flujo = planes.obtener_flujo_inversion(flujo_id)
        valoracion = planes.obtener_valoracion_inversion(valoracion_id)
        assert flujo is not None and flujo.snapshot_json is not None
        assert valoracion is not None and valoracion.snapshot_json is not None
        yield db, planes, flujo, valoracion


def test_registra_correccion_de_flujo_sin_alterar_original_ni_rendimiento(caso_inversion):
    db, planes, flujo, _ = caso_inversion
    servicio = ServicioCorreccionesAuditables(db)
    antes = planes.resumen_rendimiento_inversion(flujo.plan_id)
    snapshot = json.loads(flujo.snapshot_json)
    snapshot["monto_original"] = "1200.00"
    snapshot["equivalente_usd"] = "1200.00"

    propuesta = servicio.registrar_propuesta(
        entidad_tipo="FLUJO_INVERSION_REPOSICION",
        entidad_id=flujo.id,
        hash_original=flujo.snapshot_sha256,
        snapshot_corregido=snapshot,
        motivo="El aporte a la inversión se había cargado por un importe incorrecto",
        corregido_por="admin",
        clave_idempotencia="flujo-corr-0001",
    )

    assert propuesta.entidad_tipo == "FLUJO_INVERSION_REPOSICION"
    assert json.loads(propuesta.snapshot_corregido_json)["monto_original"] == "1200.00"
    original = planes.obtener_flujo_inversion(flujo.id)
    assert original is not None and original.snapshot_json == flujo.snapshot_json
    despues = planes.resumen_rendimiento_inversion(flujo.plan_id)
    assert despues.aportes_inversion_usd_ref == antes.aportes_inversion_usd_ref
    assert despues.resultado_total_usd_ref == antes.resultado_total_usd_ref


def test_registra_correccion_de_valuacion_sin_crear_ganancia_realizada(caso_inversion):
    db, planes, _, valoracion = caso_inversion
    servicio = ServicioCorreccionesAuditables(db)
    antes = planes.resumen_rendimiento_inversion(valoracion.plan_id)
    snapshot = json.loads(valoracion.snapshot_json)
    snapshot["valor_original"] = "1250.00"
    snapshot["equivalente_usd"] = "1250.00"

    propuesta = servicio.registrar_propuesta(
        entidad_tipo="VALUACION_INVERSION_REPOSICION",
        entidad_id=valoracion.id,
        hash_original=valoracion.snapshot_sha256,
        snapshot_corregido=snapshot,
        motivo="El valor declarado al cierre estaba mal transcripto",
        corregido_por="admin",
        clave_idempotencia="valuacion-corr-0001",
    )

    assert propuesta.entidad_tipo == "VALUACION_INVERSION_REPOSICION"
    original = planes.obtener_valoracion_inversion(valoracion.id)
    assert original is not None and original.snapshot_json == valoracion.snapshot_json
    despues = planes.resumen_rendimiento_inversion(valoracion.plan_id)
    assert despues.valor_mercado_final_usd_ref == antes.valor_mercado_final_usd_ref
    assert despues.resultado_total_usd_ref == antes.resultado_total_usd_ref


def test_rollback_si_falla_la_persistencia_de_la_correccion(caso_aporte, monkeypatch):
    db, planes, aporte = caso_aporte
    servicio = ServicioCorreccionesAuditables(db)
    ejecutar_original = db.ejecutar

    def fallar_insert(sql, params=()):
        if "INSERT INTO correcciones_auditables" in sql:
            raise RuntimeError("fallo inyectado de persistencia")
        return ejecutar_original(sql, params)

    monkeypatch.setattr(db, "ejecutar", fallar_insert)
    with pytest.raises(ErrorTransaccion, match="Transacción abortada"):
        _registrar(servicio, aporte, _snapshot_corregido(aporte, "1200.00"))
    monkeypatch.setattr(db, "ejecutar", ejecutar_original)

    assert servicio.listar_historial(
        entidad_tipo="APORTE_REPOSICION", entidad_id=aporte.id
    ) == ()
    original = planes.obtener_aporte(aporte.id)
    assert original is not None
    assert original.snapshot_sha256 == aporte.snapshot_sha256
