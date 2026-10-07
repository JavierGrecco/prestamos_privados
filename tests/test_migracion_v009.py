from pathlib import Path
import sqlite3

from infraestructura.migraciones.v009_registro_pago_v3 import aplicar


def test_v009_agrega_columns_e_indices(tmp_path: Path):
    db = sqlite3.connect(tmp_path / "v009.db")
    try:
        db.executescript("""
        CREATE TABLE prestamos (id INTEGER PRIMARY KEY, revision_base TEXT);
        CREATE TABLE pagos (id INTEGER PRIMARY KEY, estado TEXT);
        CREATE TABLE imputaciones (id INTEGER PRIMARY KEY, monto TEXT);
        """)
        class Wrapper:
            def ejecutar(self, sql, params=()): return db.execute(sql, params)
        aplicar(Wrapper())
        columnas_p = {r[1] for r in db.execute("PRAGMA table_info(prestamos)")}
        columnas_pago = {r[1] for r in db.execute("PRAGMA table_info(pagos)")}
        columnas_i = {r[1] for r in db.execute("PRAGMA table_info(imputaciones)")}
        assert "revision_prestamo" in columnas_p
        assert {"idempotency_key", "idempotency_fingerprint", "motor_version", "plan_hash", "plan_json"} <= columnas_pago
        assert {"origen", "referencias_devengamiento"} <= columnas_i
        assert db.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='ux_pagos_idempotency_key'").fetchone()
        assert db.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_pagos_motor_version'").fetchone()
    finally:
        db.close()
