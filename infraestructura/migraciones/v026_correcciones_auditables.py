"""Migración v026: bitácora inmutable para futuras correcciones de hechos financieros.

La tabla registra correcciones propuestas sin modificar los registros originales.
La aplicación aún debe aportar el servicio transaccional y conectar los informes.
"""

from ..db import BaseDatos


def aplicar(db: BaseDatos) -> None:
    db.ejecutar(
        """
        CREATE TABLE IF NOT EXISTS correcciones_auditables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entidad_tipo TEXT NOT NULL CHECK (
                entidad_tipo IN (
                    'APORTE_REPOSICION',
                    'FLUJO_INVERSION_REPOSICION',
                    'VALUACION_INVERSION_REPOSICION'
                )
            ),
            entidad_id INTEGER NOT NULL CHECK (entidad_id > 0),
            hash_original TEXT NOT NULL CHECK (
                length(hash_original) = 64
                AND hash_original NOT GLOB '*[^0-9a-f]*'
            ),
            snapshot_corregido_json TEXT NOT NULL CHECK (
                json_valid(snapshot_corregido_json)
                AND json_type(snapshot_corregido_json) = 'object'
            ),
            hash_corregido TEXT NOT NULL CHECK (
                length(hash_corregido) = 64
                AND hash_corregido NOT GLOB '*[^0-9a-f]*'
            ),
            motivo TEXT NOT NULL CHECK (
                length(trim(motivo)) BETWEEN 3 AND 1000
            ),
            corregido_por TEXT NOT NULL CHECK (
                length(trim(corregido_por)) BETWEEN 1 AND 120
            ),
            corregido_en_utc TEXT NOT NULL CHECK (
                length(trim(corregido_en_utc)) > 0
            ),
            clave_idempotencia TEXT NOT NULL UNIQUE CHECK (
                length(trim(clave_idempotencia)) BETWEEN 8 AND 160
            ),
            correccion_anterior_id INTEGER
                REFERENCES correcciones_auditables(id) ON DELETE RESTRICT,
            CHECK (
                correccion_anterior_id IS NULL OR correccion_anterior_id <> id
            )
        )
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_correcciones_auditables_entidad
        ON correcciones_auditables (entidad_tipo, entidad_id, id)
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_correcciones_auditables_no_update
        BEFORE UPDATE ON correcciones_auditables
        BEGIN
            SELECT RAISE(ABORT, 'las correcciones auditables son inmutables');
        END
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_correcciones_auditables_no_delete
        BEFORE DELETE ON correcciones_auditables
        BEGIN
            SELECT RAISE(ABORT, 'las correcciones auditables se conservan como historial');
        END
        """
    )
