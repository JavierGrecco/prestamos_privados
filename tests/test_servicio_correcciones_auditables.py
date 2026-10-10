"""Pruebas del servicio de propuestas de corrección auditable."""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json

import pytest

from aplicacion.servicios import ServicioCorreccionesAuditables
from dominio.excepciones import ErrorValidacion
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
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
