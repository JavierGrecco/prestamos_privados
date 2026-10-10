"""Aceptación del flujo explícito de inspección y actualización de schema."""

from datetime import datetime
import json
from pathlib import Path

from infraestructura import BaseDatos, verificar_backup
from infraestructura.migraciones import (
    aplicar_migraciones,
    inspeccionar_estado_migraciones,
)
from infraestructura.migraciones.gestor import (
    _asegurar_tabla_migraciones,
    _cargar_migraciones,
)
from scripts.migrar_base import main


def _crear_base_en_version(ruta: Path, version_objetivo: int) -> None:
    """Construye una base histórica real aplicando migraciones en orden."""
    with BaseDatos(ruta) as db:
        _asegurar_tabla_migraciones(db)
        for version, nombre, migrar in _cargar_migraciones():
            if version > version_objetivo:
                break
            with db.transaccion():
                migrar(db)
                db.ejecutar(
                    """
                    INSERT INTO migraciones (version, nombre, aplicada_en)
                    VALUES (?, ?, ?)
                    """,
                    (version, nombre, datetime(2026, 10, 8).isoformat()),
                )


def _json_salida(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def test_inspeccionar_base_vacia_no_crea_tablas(tmp_path: Path) -> None:
    ruta = tmp_path / "nueva.db"

    with BaseDatos(ruta) as db:
        estado = inspeccionar_estado_migraciones(db)
        tablas = {
            fila["name"]
            for fila in db.consultar(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

    assert estado.es_base_nueva is True
    assert estado.version_actual == 0
    assert estado.version_destino == 24
    assert [m.version for m in estado.pendientes] == list(range(1, 25))
    assert "migraciones" not in tablas


def test_inspeccionar_base_actualizada_no_informa_pendientes(tmp_path: Path) -> None:
    ruta = tmp_path / "actual.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        estado = inspeccionar_estado_migraciones(db)

    assert estado.historial_valido is True
    assert estado.es_base_nueva is False
    assert estado.version_actual == estado.version_destino == 24
    assert estado.pendientes == ()


def test_schema_existente_sin_historial_se_rechaza_sin_mutarlo(
    tmp_path: Path,
) -> None:
    ruta = tmp_path / "historica-sin-version.db"
    with BaseDatos(ruta) as db:
        db.ejecutar("CREATE TABLE hechos_anteriores (id INTEGER PRIMARY KEY)")
        estado = inspeccionar_estado_migraciones(db)
        tablas = {
            fila["name"]
            for fila in db.consultar(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

    assert estado.historial_valido is False
    assert estado.version_actual is None
    assert "historial de migraciones" in (estado.detalle or "").lower()
    assert "hechos_anteriores" in tablas
    assert "migraciones" not in tablas


def test_inspeccion_de_base_inexistente_no_crea_archivo(
    tmp_path: Path, capsys
) -> None:
    ruta = tmp_path / "todavia-no-existe.db"

    codigo = main([str(ruta)])
    salida = _json_salida(capsys)

    assert codigo == 0
    assert ruta.exists() is False
    assert salida["resultado"] == "BASE_INEXISTENTE"
    assert salida["version_origen"] is None
    assert salida["version_destino"] == 24
    assert salida["cambios_aplicados"] == []


def test_base_nueva_se_puede_inicializar_sin_backup(
    tmp_path: Path, capsys
) -> None:
    ruta = tmp_path / "nueva.db"

    codigo = main([str(ruta), "--aplicar"])
    salida = _json_salida(capsys)

    assert codigo == 0
    assert salida["resultado"] == "APLICADA"
    assert salida["version_origen"] == 24
    assert salida["version_destino"] == 24
    assert salida["cambios_aplicados"] == list(range(1, 25))
    assert salida["backup"] is None


def test_upgrade_existente_exige_backup_y_no_aplica_migraciones(
    tmp_path: Path, capsys
) -> None:
    ruta = tmp_path / "v015.db"
    _crear_base_en_version(ruta, 15)

    codigo = main([str(ruta), "--aplicar"])
    salida = _json_salida(capsys)

    with BaseDatos(ruta) as db:
        estado_final = inspeccionar_estado_migraciones(db)

    assert codigo == 2
    assert salida["resultado"] == "BACKUP_REQUERIDO"
    assert salida["version_origen"] == 15
    assert [m["version"] for m in salida["migraciones_pendientes"]] == [16, 17, 18, 19, 20, 21, 22, 23, 24]
    assert estado_final.version_actual == 15
    assert [m.version for m in estado_final.pendientes] == [16, 17, 18, 19, 20, 21, 22, 23, 24]


def test_upgrade_existente_crea_backup_verificado_antes_de_migrar(
    tmp_path: Path, capsys
) -> None:
    ruta = tmp_path / "v015.db"
    backup = tmp_path / "backups" / "v015-pre-migracion.db"
    _crear_base_en_version(ruta, 15)

    codigo = main([str(ruta), "--aplicar", "--backup", str(backup)])
    salida = _json_salida(capsys)

    with BaseDatos(ruta) as db:
        estado_final = inspeccionar_estado_migraciones(db)
    evidencia = verificar_backup(backup)

    assert codigo == 0
    assert salida["resultado"] == "APLICADA"
    assert salida["version_origen"] == 24
    assert salida["version_destino"] == 24
    assert salida["cambios_aplicados"] == [16, 17, 18, 19, 20, 21, 22, 23, 24]
    assert salida["backup"]["integridad_ok"] is True
    assert evidencia.integridad.ok is True
    assert evidencia.ruta_manifest.exists()
    assert estado_final.historial_valido is True
    assert estado_final.pendientes == ()


def test_upgrade_v017_preserva_cuentas_y_agrega_vinculo_opcional_y_garantias(
    tmp_path: Path,
) -> None:
    ruta = tmp_path / "v017-con-usuarios.db"
    _crear_base_en_version(ruta, 17)

    with BaseDatos(ruta) as db:
        db.ejecutar(
            """
            INSERT INTO usuarios_app
                (username, nombre, rol, password_hash, activo,
                 intentos_login_fallidos, creado_en, actualizado_en)
            VALUES ('admin', 'Admin local', 'ADMIN', 'hash-de-prueba',
                    1, 0, '2026-10-08', '2026-10-08')
            """
        )
        antes = db.consultar_uno(
            "SELECT id, username, rol FROM usuarios_app WHERE username = 'admin'"
        )
        aplicadas = aplicar_migraciones(db)
        despues = db.consultar_uno(
            "SELECT id, username, rol, revision_sesion, persona_id "
            "FROM usuarios_app WHERE username = 'admin'"
        )
        estado = inspeccionar_estado_migraciones(db)

    assert aplicadas == [18, 19, 20, 21, 22, 23, 24]
    assert despues["id"] == antes["id"]
    assert despues["username"] == antes["username"]
    assert despues["rol"] == antes["rol"] == "ADMIN"
    assert despues["revision_sesion"] == 1
    assert despues["persona_id"] is None
    assert estado.version_actual == estado.version_destino == 24
    assert estado.pendientes == ()
    with BaseDatos(ruta) as db:
        assert db.consultar("PRAGMA foreign_key_check") == []

def test_base_con_schema_sin_historial_no_se_migra_automaticamente(
    tmp_path: Path, capsys
) -> None:
    ruta = tmp_path / "legacy-sin-historial.db"
    backup = tmp_path / "backup.db"
    with BaseDatos(ruta) as db:
        db.ejecutar("CREATE TABLE movimientos_legacy (id INTEGER PRIMARY KEY)")

    codigo = main([str(ruta), "--aplicar", "--backup", str(backup)])
    salida = _json_salida(capsys)

    with BaseDatos(ruta) as db:
        tablas = {
            fila["name"]
            for fila in db.consultar(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

    assert codigo == 2
    assert salida["resultado"] == "RECHAZADO_HISTORIAL"
    assert "migraciones" not in tablas
    assert backup.exists() is False
