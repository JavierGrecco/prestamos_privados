"""Migración v011: observaciones append-only del modo SOMBRA V3."""


def aplicar(db) -> None:
    db.ejecutar(
        """
        CREATE TABLE IF NOT EXISTS observaciones_sombra_v3 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestamo_id INTEGER NOT NULL,
            pago_legacy_id INTEGER,
            fingerprint TEXT NOT NULL,
            tipo TEXT NOT NULL
                CHECK (tipo IN ('DIVERGENCIA', 'ERROR_SOMBRA')),
            resumen TEXT NOT NULL,
            detalle_json TEXT,
            correlacion_id TEXT,
            motor_version TEXT NOT NULL,
            creado_en TEXT NOT NULL
        )
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_sombra_prestamo_fecha
        ON observaciones_sombra_v3(prestamo_id, creado_en, id)
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_sombra_fingerprint
        ON observaciones_sombra_v3(fingerprint)
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_sombra_tipo
        ON observaciones_sombra_v3(tipo, creado_en, id)
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_sombra_no_update
        BEFORE UPDATE ON observaciones_sombra_v3
        BEGIN
            SELECT RAISE(ABORT, 'Las observaciones SOMBRA son inmutables');
        END
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_sombra_no_delete
        BEFORE DELETE ON observaciones_sombra_v3
        BEGIN
            SELECT RAISE(ABORT, 'Las observaciones SOMBRA no se eliminan');
        END
        """
    )
