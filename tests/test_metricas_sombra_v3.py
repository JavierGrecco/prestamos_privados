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
    assert metricas.primera_observacion is None
    assert metricas.ultima_observacion is None
    assert metricas.por_tipo == ()
    assert metricas.por_prestamo == ()
    assert metricas.por_fingerprint == ()


def test_metricas_agregan_por_tipo_prestamo_y_fingerprint(db):
    with db.transaccion():
        _insertar(db, 1, "fp-a", "DIVERGENCIA", "d1", "2026-10-07T10:00:00")
        _insertar(db, 1, "fp-a", "DIVERGENCIA", "d2", "2026-10-07T10:05:00")
        _insertar(db, 2, "fp-b", "ERROR_SOMBRA", "e1", "2026-10-07T11:00:00")
        _insertar(db, 2, "fp-c", "ERROR_SOMBRA", "e2", "2026-10-07T12:00:00")

    metricas = ServicioMetricasSombraV3(db).obtener()

    assert metricas.total_observaciones == 4
    assert metricas.divergencias == 2
    assert metricas.errores_sombra == 2
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
