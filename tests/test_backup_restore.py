"""Pruebas de integridad, backup verificable y restore drill sobre SQLite."""

from pathlib import Path

import pytest

from infraestructura import (
    BaseDatos,
    ErrorBackup,
    ErrorRestore,
    crear_backup_verificado,
    restaurar_backup_verificado,
    verificar_backup,
    verificar_integridad_sqlite,
)
from infraestructura.migraciones import aplicar_migraciones


def _crear_base_con_datos(ruta: Path) -> None:
    with BaseDatos(ruta) as db:
        db.ejecutar(
            """
            CREATE TABLE cuentas (
                id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL
            )
            """
        )
        db.ejecutar(
            """
            CREATE TABLE movimientos (
                id INTEGER PRIMARY KEY,
                cuenta_id INTEGER NOT NULL,
                monto TEXT NOT NULL,
                FOREIGN KEY (cuenta_id) REFERENCES cuentas(id)
            )
            """
        )
        with db.transaccion():
            db.ejecutar(
                "INSERT INTO cuentas (nombre) VALUES (?)",
                ("cuenta-1",),
            )
            cuenta_id = db.ultimo_id_insertado()
            for monto in ("100.00", "25.50", "10.25"):
                db.ejecutar(
                    "INSERT INTO movimientos (cuenta_id, monto) VALUES (?, ?)",
                    (cuenta_id, monto),
                )


class TestIntegridadOperativa:
    def test_integridad_devuelve_resultado_verificable(self, tmp_path: Path):
        ruta = tmp_path / "origen.db"
        _crear_base_con_datos(ruta)

        resultado = verificar_integridad_sqlite(ruta)

        assert resultado.ok is True
        assert resultado.quick_check == ("ok",)
        assert resultado.integrity_check == ("ok",)
        assert resultado.foreign_key_errores == ()


class TestBackup:
    def test_backup_funciona_con_wal_activo_y_es_autocontenido(
        self, tmp_path: Path
    ):
        origen = tmp_path / "origen.db"
        backup = tmp_path / "backup.db"

        with BaseDatos(origen) as db:
            db.ejecutar(
                "CREATE TABLE movimientos (id INTEGER PRIMARY KEY, monto TEXT NOT NULL)"
            )
            with db.transaccion():
                db.ejecutar(
                    "INSERT INTO movimientos (monto) VALUES (?)",
                    ("100.00",),
                )

            resultado = crear_backup_verificado(origen, backup)

            assert resultado.ruta_backup == backup
            assert resultado.ruta_manifest.exists()
            assert resultado.bytes == backup.stat().st_size
            assert len(resultado.sha256) == 64
            assert resultado.integridad.ok is True

            # La fuente sigue abierta y el WAL permanece activo mientras se
            # crea el backup. El backup no depende de cerrar la conexión.
            assert (tmp_path / "origen.db-wal").exists()
            assert db.consultar_uno(
                "SELECT COUNT(*) AS total FROM movimientos"
            )["total"] == 1

        evidencia = verificar_backup(backup)
        assert evidencia.sha256 == resultado.sha256
        assert evidencia.integridad.ok is True

    def test_no_sobrescribe_backup_existente(self, tmp_path: Path):
        origen = tmp_path / "origen.db"
        backup = tmp_path / "backup.db"
        _crear_base_con_datos(origen)
        backup.write_bytes(b"backup-anterior")

        with pytest.raises(ErrorBackup):
            crear_backup_verificado(origen, backup)

        assert backup.read_bytes() == b"backup-anterior"

    def test_detecta_manifiesto_alterado(self, tmp_path: Path):
        origen = tmp_path / "origen.db"
        backup = tmp_path / "backup.db"
        _crear_base_con_datos(origen)
        crear_backup_verificado(origen, backup)

        manifest = backup.with_name(backup.name + ".manifest.json")
        contenido = manifest.read_text(encoding="utf-8")
        manifest.write_text(
            contenido.replace('"sha256":', '"sha256x":'),
            encoding="utf-8",
        )

        with pytest.raises(ErrorBackup):
            verificar_backup(backup)


class TestRestoreDrill:
    def test_restore_reproduce_datos_y_pasa_integridad(self, tmp_path: Path):
        origen = tmp_path / "origen.db"
        backup = tmp_path / "backup.db"
        restore = tmp_path / "restore.db"
        _crear_base_con_datos(origen)

        evidencia_backup = crear_backup_verificado(origen, backup)
        evidencia_restore = restaurar_backup_verificado(backup, restore)

        assert evidencia_restore.sha256 == evidencia_backup.sha256
        assert evidencia_restore.bytes == evidencia_backup.bytes
        assert evidencia_restore.integridad.ok is True

        with BaseDatos(restore) as db:
            total = db.consultar_uno(
                "SELECT COUNT(*) AS total FROM movimientos"
            )
            suma = db.consultar_uno(
                "SELECT SUM(CAST(monto AS REAL)) AS total FROM movimientos"
            )
            assert total["total"] == 3
            assert suma["total"] == pytest.approx(135.75)

    def test_no_sobrescribe_restore_existente(self, tmp_path: Path):
        origen = tmp_path / "origen.db"
        backup = tmp_path / "backup.db"
        restore = tmp_path / "restore.db"
        _crear_base_con_datos(origen)
        crear_backup_verificado(origen, backup)
        restore.write_bytes(b"restauracion-anterior")

        with pytest.raises(ErrorRestore):
            restaurar_backup_verificado(backup, restore)

        assert restore.read_bytes() == b"restauracion-anterior"

    def test_restore_rechaza_backup_tamperizado(self, tmp_path: Path):
        origen = tmp_path / "origen.db"
        backup = tmp_path / "backup.db"
        restore = tmp_path / "restore.db"
        _crear_base_con_datos(origen)
        crear_backup_verificado(origen, backup)

        with backup.open("ab") as archivo:
            archivo.write(b"tamper")

        with pytest.raises(ErrorBackup):
            restaurar_backup_verificado(backup, restore)

        assert not restore.exists()


class TestBackupConSchemaReal:
    def test_backup_y_restore_de_schema_actual(self, tmp_path: Path):
        origen = tmp_path / "origen_schema.db"
        backup = tmp_path / "backup_schema.db"
        restore = tmp_path / "restore_schema.db"

        with BaseDatos(origen) as db:
            aplicar_migraciones(db)
            resultado = crear_backup_verificado(origen, backup)

        assert resultado.integridad.ok is True

        restore_resultado = restaurar_backup_verificado(backup, restore)
        assert restore_resultado.integridad.ok is True

        with BaseDatos(restore) as db:
            assert db.consultar_uno(
                "SELECT MAX(version) AS v FROM migraciones"
            )["v"] == 17
