"""Migración v009: infraestructura mínima para registro de pagos V3."""

def aplicar(db) -> None:
    db.ejecutar("ALTER TABLE prestamos ADD COLUMN revision_prestamo INTEGER NOT NULL DEFAULT 0")
    db.ejecutar("ALTER TABLE pagos ADD COLUMN idempotency_key TEXT")
    db.ejecutar("ALTER TABLE pagos ADD COLUMN idempotency_fingerprint TEXT")
    db.ejecutar("ALTER TABLE pagos ADD COLUMN motor_version TEXT NOT NULL DEFAULT 'LEGACY'")
    db.ejecutar("ALTER TABLE pagos ADD COLUMN plan_hash TEXT")
    db.ejecutar("ALTER TABLE pagos ADD COLUMN plan_json TEXT")
    db.ejecutar("ALTER TABLE imputaciones ADD COLUMN origen TEXT NOT NULL DEFAULT 'SALDO_CONTRACTUAL'")
    db.ejecutar("ALTER TABLE imputaciones ADD COLUMN referencias_devengamiento TEXT NOT NULL DEFAULT '[]'")
    db.ejecutar("CREATE UNIQUE INDEX IF NOT EXISTS ux_pagos_idempotency_key ON pagos(idempotency_key) WHERE idempotency_key IS NOT NULL")
    db.ejecutar("CREATE INDEX IF NOT EXISTS idx_pagos_motor_version ON pagos(motor_version)")
