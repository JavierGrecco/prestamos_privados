"""Pruebas de esquema para la bitácora de correcciones auditables v026."""

import pytest

from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones, version_actual


def _insertar_correccion(db, *, clave="correccion-0001"):
    db.ejecutar(
        """
        INSERT INTO correcciones_auditables (
            entidad_tipo, entidad_id, hash_original,
            snapshot_corregido_json, hash_corregido, motivo,
            corregido_por, corregido_en_utc, clave_idempotencia
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "APORTE_REPOSICION",
            7,
            "a" * 64,
            '{"monto_ars":"1250.00"}',
            "b" * 64,
            "Corrección de un importe mal cargado",
            "admin",
            "2026-10-10T12:00:00+00:00",
            clave,
        ),
    )


def test_migracion_v026_crea_bitacora_y_es_repetible(tmp_path):
    with BaseDatos(tmp_path / "migracion.db") as db:
        aplicar_migraciones(db)
        assert version_actual(db) == 26
        _insertar_correccion(db)
        aplicar_migraciones(db)
        assert db.consultar_uno(
            "SELECT COUNT(*) AS total FROM correcciones_auditables"
        )["total"] == 1


def test_correccion_es_inmutable_y_no_se_puede_borrar(tmp_path):
    with BaseDatos(tmp_path / "inmutable.db") as db:
        aplicar_migraciones(db)
        _insertar_correccion(db)
        with pytest.raises(Exception, match="inmutables"):
            db.ejecutar(
                "UPDATE correcciones_auditables SET motivo = 'otro motivo' WHERE id = 1"
            )
        with pytest.raises(Exception, match="historial"):
            db.ejecutar("DELETE FROM correcciones_auditables WHERE id = 1")


def test_clave_idempotencia_no_se_puede_reutilizar(tmp_path):
    with BaseDatos(tmp_path / "idempotencia.db") as db:
        aplicar_migraciones(db)
        _insertar_correccion(db)
        with pytest.raises(Exception):
            _insertar_correccion(db)


@pytest.mark.parametrize(
    "entidad_tipo,entidad_id,hash_original,snapshot,hash_corregido,motivo,usuario,clave",
    [
        ("ENTIDAD_DESCONOCIDA", 7, "a" * 64, '{"x":1}', "b" * 64, "Motivo válido", "admin", "clave-0001"),
        ("APORTE_REPOSICION", 0, "a" * 64, '{"x":1}', "b" * 64, "Motivo válido", "admin", "clave-0001"),
        ("APORTE_REPOSICION", 7, "x", '{"x":1}', "b" * 64, "Motivo válido", "admin", "clave-0001"),
        ("APORTE_REPOSICION", 7, "a" * 64, '[]', "b" * 64, "Motivo válido", "admin", "clave-0001"),
        ("APORTE_REPOSICION", 7, "a" * 64, '{"x":1}', "b" * 64, " ", "admin", "clave-0001"),
    ],
)
def test_schema_rechaza_correcciones_invalidas(
    tmp_path, entidad_tipo, entidad_id, hash_original, snapshot,
    hash_corregido, motivo, usuario, clave
):
    with BaseDatos(tmp_path / "validacion.db") as db:
        aplicar_migraciones(db)
        with pytest.raises(Exception):
            db.ejecutar(
                """
                INSERT INTO correcciones_auditables (
                    entidad_tipo, entidad_id, hash_original,
                    snapshot_corregido_json, hash_corregido, motivo,
                    corregido_por, corregido_en_utc, clave_idempotencia
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entidad_tipo, entidad_id, hash_original, snapshot,
                    hash_corregido, motivo, usuario,
                    "2026-10-10T12:00:00+00:00", clave,
                ),
            )
