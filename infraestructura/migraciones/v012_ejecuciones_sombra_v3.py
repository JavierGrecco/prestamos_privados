"""Migración v012: registro completo de ejecuciones SOMBRA V3."""


def aplicar(db) -> None:
    db.ejecutar(
        """
        CREATE TABLE IF NOT EXISTS ejecuciones_sombra_v3 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestamo_id INTEGER NOT NULL,
            pago_legacy_id INTEGER,
            fingerprint TEXT NOT NULL,
            resultado TEXT NOT NULL
                CHECK (resultado IN ('SIN_DIVERGENCIA', 'DIVERGENCIA', 'ERROR_SOMBRA')),
            revision_snapshot INTEGER,
            resumen TEXT,
            detalle_json TEXT,
            motor_version TEXT NOT NULL,
            creado_en TEXT NOT NULL
        )
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_ejec_sombra_prestamo_fecha
        ON ejecuciones_sombra_v3(prestamo_id, creado_en, id)
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_ejec_sombra_resultado
        ON ejecuciones_sombra_v3(resultado, creado_en, id)
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_ejec_sombra_fingerprint
        ON ejecuciones_sombra_v3(fingerprint)
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_ejec_sombra_no_update
        BEFORE UPDATE ON ejecuciones_sombra_v3
        BEGIN
            SELECT RAISE(ABORT, 'Las ejecuciones SOMBRA son inmutables');
        END
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_ejec_sombra_no_delete
        BEFORE DELETE ON ejecuciones_sombra_v3
        BEGIN
            SELECT RAISE(ABORT, 'Las ejecuciones SOMBRA no se eliminan');
        END
        """
    )
