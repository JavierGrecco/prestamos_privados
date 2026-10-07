from pathlib import Path
import sqlite3

from infraestructura.migraciones.v010_devengamientos_v3 import aplicar


def test_v010_crea_tabla_indices_triggers_y_unico(tmp_path: Path):
    db = sqlite3.connect(tmp_path / "v010.db")
    try:
        db.executescript("""
        CREATE TABLE dev_placeholder (id INTEGER PRIMARY KEY);
        CREATE TABLE prestamos (id INTEGER PRIMARY KEY);
        CREATE TABLE versiones_tasa (id INTEGER PRIMARY KEY, prestamo_id INTEGER);
        CREATE TABLE cuotas (id INTEGER PRIMARY KEY, version_id INTEGER);
        """)
        class Wrapper:
            def ejecutar(self, sql, params=()):
                return db.execute(sql, params)
        aplicar(Wrapper())
        columnas = {r[1] for r in db.execute("PRAGMA table_info(devengamientos)")}
        assert {"prestamo_id", "cuota_id", "concepto", "monto", "fecha_desde", "fecha_hasta", "huella", "motor_version"} <= columnas
        indices = {r[1] for r in db.execute("PRAGMA index_list(devengamientos)")}
        assert "idx_devengamientos_prestamo_fecha" in indices
        assert "idx_devengamientos_cuota_fecha" in indices
        triggers = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
        assert "trg_devengamientos_no_update" in triggers
        assert "trg_devengamientos_no_delete" in triggers
    finally:
        db.close()
