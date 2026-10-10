"""Migración v022: guarda snapshots auditables del simulador de reposición.

Los snapshots son informes de análisis, no contratos ni pagos. Se conservan
como evidencia inmutable de los supuestos y resultados que vio el usuario.
"""


def aplicar(db) -> None:
    db.ejecutar(
        """
        CREATE TABLE IF NOT EXISTS planes_reposicion_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL CHECK (length(trim(nombre)) BETWEEN 1 AND 120),
            tipo_plan TEXT NOT NULL CHECK (
                tipo_plan IN ('REPOSICION_INTERNA', 'PRESTAMO_ENTRE_PERSONAS')
            ),
            fecha_desembolso TEXT NOT NULL,
            capital_original_ars TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            snapshot_sha256 TEXT NOT NULL CHECK (length(snapshot_sha256) = 64),
            creado_por TEXT NOT NULL CHECK (length(trim(creado_por)) > 0),
            creado_en TEXT NOT NULL
        )
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_planes_reposicion_snapshots_fecha
        ON planes_reposicion_snapshots (creado_en DESC, id DESC)
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_planes_reposicion_snapshot_no_update
        BEFORE UPDATE ON planes_reposicion_snapshots
        BEGIN
            SELECT RAISE(ABORT, 'snapshot de reposición inmutable; guarde una nueva versión');
        END
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_planes_reposicion_snapshot_no_delete
        BEFORE DELETE ON planes_reposicion_snapshots
        BEGIN
            SELECT RAISE(ABORT, 'snapshot de reposición inmutable; no se puede borrar');
        END
        """
    )
