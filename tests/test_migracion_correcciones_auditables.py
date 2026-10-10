"""Pruebas de esquema para la bitácora de correcciones auditables v026."""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones, version_actual
from infraestructura.migraciones.gestor import _cargar_migraciones
from infraestructura.repositorios import PlanesReposicionRepo


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



def test_migracion_v026_desde_v025_conserva_hechos_existentes(tmp_path):
    """Actualiza un esquema v025 con datos y conserva el snapshot financiero."""
    with BaseDatos(tmp_path / "desde_v025.db") as db:
        db.ejecutar(
            """
            CREATE TABLE migraciones (
                version INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                aplicada_en TEXT NOT NULL,
                hash TEXT
            )
            """
        )
        for version, nombre, funcion in _cargar_migraciones():
            if version >= 26:
                break
            with db.transaccion():
                funcion(db)
                db.ejecutar(
                    "INSERT INTO migraciones (version, nombre, aplicada_en) VALUES (?, ?, ?)",
                    (version, nombre, "2026-10-10T12:00:00"),
                )

        assert version_actual(db) == 25
        planes = PlanesReposicionRepo(db)
        plan_id, _ = planes.crear_plan_con_snapshot(
            nombre="Plan histórico v025",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date.today() - timedelta(days=30),
            capital_original_ars=Decimal("10000.00"),
            datos={"origen": "prueba-migracion-v025"},
            creado_por="admin",
        )
        aporte_id = planes.registrar_aporte(
            plan_id,
            fecha_aporte=date.today() - timedelta(days=1),
            monto_ars=Decimal("1500.00"),
            cotizacion_ars_por_usd=Decimal("1000.000000"),
            naturaleza_cotizacion="SUPUESTO",
            fuente_cotizacion="",
            referencia="aporte previo a v026",
            nota="",
            creado_por="admin",
        )
        antes = planes.obtener_aporte(aporte_id)
        assert antes is not None

        assert aplicar_migraciones(db) == [26]
        assert version_actual(db) == 26

        despues = planes.obtener_aporte(aporte_id)
        assert despues is not None
        assert despues.snapshot_json == antes.snapshot_json
        assert despues.snapshot_sha256 == antes.snapshot_sha256
        assert db.consultar_uno(
            "SELECT COUNT(*) AS total FROM correcciones_auditables"
        )["total"] == 0
        assert db.consultar("PRAGMA foreign_key_check") == []
