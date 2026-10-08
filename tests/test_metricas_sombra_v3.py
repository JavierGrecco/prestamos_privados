"""Tests del read model de métricas SOMBRA V3."""
from pathlib import Path

import pytest

from aplicacion.servicios.metricas_sombra_v3 import ServicioMetricasSombraV3
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "metricas_sombra.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield db


def _insertar_ejecucion(db, prestamo_id, fingerprint, resultado, creado_en):
    db.ejecutar(
        """INSERT INTO ejecuciones_sombra_v3
           (prestamo_id, pago_legacy_id, fingerprint, resultado,
            revision_snapshot, resumen, detalle_json, motor_version, creado_en)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'V3-SOMBRA', ?)""",
        (
            prestamo_id,
            None,
            fingerprint,
            resultado,
            0,
            None if resultado == "SIN_DIVERGENCIA" else "detalle",
            "{}",
            creado_en,
        ),
    )


def _insertar(db, prestamo_id, fingerprint, tipo, resumen, creado_en):
    db.ejecutar(
        """INSERT INTO observaciones_sombra_v3
           (prestamo_id, pago_legacy_id, fingerprint, tipo, resumen,
            detalle_json, correlacion_id, motor_version, creado_en)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'V3-SOMBRA', ?)""",
        (
            prestamo_id,
            None,
            fingerprint,
            tipo,
            resumen,
            "{}",
            None,
            creado_en,
        ),
    )


def test_metricas_vacias_son_cero_y_sin_fechas(db):
    metricas = ServicioMetricasSombraV3(db).obtener()

    assert metricas.total_observaciones == 0
    assert metricas.divergencias == 0
    assert metricas.errores_sombra == 0
    assert metricas.prestamos_con_observaciones == 0
    assert metricas.fingerprints_distintos == 0
    assert metricas.ejecuciones_sombra == 0
    assert metricas.tasa_coincidencia is None
    assert metricas.tasa_divergencia is None
    assert metricas.tasa_error is None
    assert metricas.primera_observacion is None
    assert metricas.ultima_observacion is None
    assert metricas.por_tipo == ()
    assert metricas.por_prestamo == ()
    assert metricas.por_fingerprint == ()


def test_metricas_agregan_por_tipo_prestamo_y_fingerprint(db):
    with db.transaccion():
        _insertar_ejecucion(db, 1, "fp-a", "SIN_DIVERGENCIA", "2026-10-07T09:00:00")
        _insertar_ejecucion(db, 1, "fp-b", "DIVERGENCIA", "2026-10-07T09:30:00")
        _insertar_ejecucion(db, 2, "fp-c", "ERROR_SOMBRA", "2026-10-07T09:45:00")

    with db.transaccion():
        _insertar(db, 1, "fp-a", "DIVERGENCIA", "d1", "2026-10-07T10:00:00")
        _insertar(db, 1, "fp-a", "DIVERGENCIA", "d2", "2026-10-07T10:05:00")
        _insertar(db, 2, "fp-b", "ERROR_SOMBRA", "e1", "2026-10-07T11:00:00")
        _insertar(db, 2, "fp-c", "ERROR_SOMBRA", "e2", "2026-10-07T12:00:00")

    metricas = ServicioMetricasSombraV3(db).obtener()

    assert metricas.total_observaciones == 4
    assert metricas.divergencias == 2
    assert metricas.errores_sombra == 2
    assert metricas.ejecuciones_sombra == 3
    assert metricas.ejecuciones_sin_divergencia == 1
    assert metricas.ejecuciones_con_divergencia == 1
    assert metricas.ejecuciones_con_error == 1
    assert metricas.tasa_coincidencia == 1 / 3
    assert metricas.tasa_divergencia == 1 / 3
    assert metricas.tasa_error == 1 / 3
    assert metricas.prestamos_con_observaciones == 2
    assert metricas.fingerprints_distintos == 3
    assert metricas.primera_observacion == "2026-10-07T10:00:00"
    assert metricas.ultima_observacion == "2026-10-07T12:00:00"
    assert tuple((x.etiqueta, x.cantidad) for x in metricas.por_tipo) == (
        ("DIVERGENCIA", 2),
        ("ERROR_SOMBRA", 2),
    )


def test_metricas_filtradas_por_prestamo_no_contaminan_el_total_global(db):
    with db.transaccion():
        _insertar(db, 1, "fp-a", "DIVERGENCIA", "d1", "2026-10-07T10:00:00")
        _insertar(db, 2, "fp-b", "ERROR_SOMBRA", "e1", "2026-10-07T11:00:00")

    metricas = ServicioMetricasSombraV3(db).obtener(prestamo_id=1)

    assert metricas.total_observaciones == 1
    assert metricas.divergencias == 1
    assert metricas.errores_sombra == 0
    assert metricas.prestamos_con_observaciones == 1
    assert metricas.fingerprints_distintos == 1
    assert tuple((x.etiqueta, x.cantidad) for x in metricas.por_prestamo) == (
        ("1", 1),
    )


def test_metricas_filtradas_rechazan_prestamo_invalido(db):
    with pytest.raises(ValueError, match="positivo"):
        ServicioMetricasSombraV3(db).obtener(prestamo_id=0)


def test_servicio_lista_incidencias_por_tipo_y_limite(db):
    for i in range(3):
        _insertar(
            db,
            10,
            f"fp-div-{i}",
            "DIVERGENCIA",
            f"divergencia-{i}",
            f"2026-10-08T10:0{i}:00",
        )
    _insertar(
        db,
        10,
        "fp-err",
        "ERROR_SOMBRA",
        "error-1",
        "2026-10-08T11:00:00",
    )

    servicio = ServicioMetricasSombraV3(db)

    todas = servicio.observaciones(limite=2)
    assert len(todas) == 2
    assert todas[0]["id"] > todas[1]["id"]

    divergencias = servicio.observaciones(
        tipo="DIVERGENCIA",
        limite=2,
    )
    assert len(divergencias) == 2
    assert all(x["tipo"] == "DIVERGENCIA" for x in divergencias)


def test_servicio_rechaza_filtros_invalidos(db):
    servicio = ServicioMetricasSombraV3(db)

    with pytest.raises(ValueError, match="tipo"):
        servicio.observaciones(tipo="OTRO")

    with pytest.raises(ValueError, match="positivo"):
        servicio.observaciones(limite=0)

    with pytest.raises(ValueError, match="positivo"):
        servicio.observaciones(prestamo_id=0)
