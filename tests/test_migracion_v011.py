from pathlib import Path

import pytest

from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones, version_actual


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "v011.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield db


def test_v011_crea_tabla_indices_y_triggers(db):
    assert version_actual(db) == 18

    columnas = {
        fila["name"]
        for fila in db.consultar("PRAGMA table_info(observaciones_sombra_v3)")
    }
    assert {
        "prestamo_id",
        "pago_legacy_id",
        "fingerprint",
        "tipo",
        "resumen",
        "detalle_json",
        "correlacion_id",
        "motor_version",
        "creado_en",
    } <= columnas

    indices = {
        fila["name"]
        for fila in db.consultar("PRAGMA index_list(observaciones_sombra_v3)")
    }
    assert "idx_sombra_prestamo_fecha" in indices
    assert "idx_sombra_fingerprint" in indices
    assert "idx_sombra_tipo" in indices

    triggers = {
        fila["name"]
        for fila in db.consultar(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        )
    }
    assert "trg_sombra_no_update" in triggers
    assert "trg_sombra_no_delete" in triggers


def test_v011_observaciones_son_append_only(db):
    with db.transaccion():
        db.ejecutar(
            """INSERT INTO observaciones_sombra_v3
               (prestamo_id, fingerprint, tipo, resumen, motor_version, creado_en)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (1, "abc", "DIVERGENCIA", "x", "V3-SOMBRA", "2026-10-07T00:00:00"),
        )

    with pytest.raises(Exception, match="inmutables"):
        db.ejecutar(
            "UPDATE observaciones_sombra_v3 SET resumen = ? WHERE id = ?",
            ("cambio", 1),
        )

    with pytest.raises(Exception, match="no se eliminan"):
        db.ejecutar(
            "DELETE FROM observaciones_sombra_v3 WHERE id = ?",
            (1,),
        )
