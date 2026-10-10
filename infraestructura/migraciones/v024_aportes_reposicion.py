"""Migración v024: registro inmutable de aportes destinados a reposición propia."""

from ..db import BaseDatos


def aplicar(db: BaseDatos) -> None:
    db.ejecutar(
        """
        CREATE TABLE IF NOT EXISTS aportes_reposicion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL REFERENCES planes_reposicion(id) ON DELETE RESTRICT,
            fecha_aporte TEXT NOT NULL,
            monto_ars TEXT NOT NULL CHECK (length(trim(monto_ars)) > 0 AND CAST(monto_ars AS NUMERIC) > 0),
            cotizacion_ars_por_usd TEXT NOT NULL CHECK (length(trim(cotizacion_ars_por_usd)) > 0 AND CAST(cotizacion_ars_por_usd AS NUMERIC) > 0),
            equivalente_usd TEXT NOT NULL,
            naturaleza_cotizacion TEXT NOT NULL CHECK (
                naturaleza_cotizacion IN ('OBSERVADA', 'SUPUESTO')
            ),
            CHECK (
                naturaleza_cotizacion <> 'OBSERVADA' OR
                length(trim(coalesce(fuente_cotizacion, ''))) > 0
            ),
            fuente_cotizacion TEXT,
            referencia TEXT,
            nota TEXT,
            snapshot_json TEXT NOT NULL,
            snapshot_sha256 TEXT NOT NULL CHECK (length(snapshot_sha256) = 64),
            creado_por TEXT NOT NULL CHECK (length(trim(creado_por)) > 0),
            creado_en TEXT NOT NULL
        )
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_aportes_reposicion_plan_fecha
        ON aportes_reposicion (plan_id, fecha_aporte, id)
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_aportes_reposicion_solo_plan_interno_activo
        BEFORE INSERT ON aportes_reposicion
        WHEN COALESCE(
            (
                SELECT estado = 'ACTIVO' AND tipo_plan = 'REPOSICION_INTERNA'
                FROM planes_reposicion WHERE id = NEW.plan_id
            ),
            0
        ) <> 1
        BEGIN
            SELECT RAISE(ABORT, 'solo se registran aportes en un plan interno activo');
        END
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_aportes_reposicion_no_update
        BEFORE UPDATE ON aportes_reposicion
        BEGIN
            SELECT RAISE(ABORT, 'los aportes de reposición son inmutables; no se editan ni se borran');
        END
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_aportes_reposicion_no_delete
        BEFORE DELETE ON aportes_reposicion
        BEGIN
            SELECT RAISE(ABORT, 'los aportes de reposición se conservan como historial');
        END
        """
    )
    db.ejecutar(
        """
        CREATE TRIGGER IF NOT EXISTS trg_aportes_reposicion_actualizar_plan
        AFTER INSERT ON aportes_reposicion
        BEGIN
            UPDATE planes_reposicion
            SET actualizado_en = NEW.creado_en
            WHERE id = NEW.plan_id AND estado = 'ACTIVO';
        END
        """
    )
