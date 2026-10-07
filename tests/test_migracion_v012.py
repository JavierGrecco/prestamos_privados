from pathlib import Path

import pytest

from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones, version_actual


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "v012.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield db


def test_v012_crea_tabla_e_indices(db):
    assert version_actual(db) == 12

    columnas = {
        fila["name"]
        for fila in db.consultar(
            "PRAGMA table_info(ejecuciones_sombra_v3)"
        )
    }
    assert {
        "prestamo_id",
        "pago_legacy_id",
        "fingerprint",
        "resultado",
        "revision_snapshot",
        "resumen",
        "detalle_json",
        "motor_version",
        "creado_en",
    } <= columnas

    indices = {
        fila["name"]
        for fila in db.consultar(
            "PRAGMA index_list(ejecuciones_sombra_v3)"
        )
    }
    assert "idx_ejec_sombra_prestamo_fecha" in indices
    assert "idx_ejec_sombra_resultado" in indices
    assert "idx_ejec_sombra_fingerprint" in indices


def test_v012_es_append_only(db):
    with db.transaccion():
        db.ejecutar(
            """INSERT INTO ejecuciones_sombra_v3
               (prestamo_id, fingerprint, resultado, motor_version, creado_en)
               VALUES (?, ?, ?, ?, ?)""",
            (1, "fp", "SIN_DIVERGENCIA", "V3-SOMBRA", "2026-10-07T00:00:00"),
        )

    with pytest.raises(Exception, match="inmutables"):
        db.ejecutar(
            "UPDATE ejecuciones_sombra_v3 SET resumen=? WHERE id=?",
            ("cambio", 1),
        )

    with pytest.raises(Exception, match="no se eliminan"):
        db.ejecutar(
            "DELETE FROM ejecuciones_sombra_v3 WHERE id=?",
            (1,),
        )


def test_v012_rechaza_resultado_desconocido(db):
    with pytest.raises(Exception):
        db.ejecutar(
            """INSERT INTO ejecuciones_sombra_v3
               (prestamo_id, fingerprint, resultado, motor_version, creado_en)
               VALUES (?, ?, ?, ?, ?)""",
            (1, "fp", "OTRO", "V3-SOMBRA", "2026-10-07T00:00:00"),
        )
