"""Migración v025: flujos y valuaciones declaradas de inversiones del plan interno."""

from ..db import BaseDatos


def aplicar(db: BaseDatos) -> None:
    db.ejecutar(
        """
        CREATE TABLE IF NOT EXISTS flujos_inversion_reposicion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL REFERENCES planes_reposicion(id) ON DELETE RESTRICT,
            fecha_flujo TEXT NOT NULL,
            tipo_flujo TEXT NOT NULL CHECK (
                tipo_flujo IN (
                    'APORTE_INVERSION',
                    'RESCATE',
                    'DISTRIBUCION',
                    'COSTO_IMPUESTO_EXTERNO'
                )
            ),
            moneda TEXT NOT NULL CHECK (moneda IN ('ARS', 'USD')),
            monto_original TEXT NOT NULL CHECK (
                length(trim(monto_original)) > 0 AND CAST(monto_original AS NUMERIC) > 0
            ),
            cotizacion_ars_por_usd TEXT,
            equivalente_usd TEXT NOT NULL CHECK (
                length(trim(equivalente_usd)) > 0 AND CAST(equivalente_usd AS NUMERIC) >= 0
            ),
            naturaleza_cotizacion TEXT NOT NULL CHECK (
                naturaleza_cotizacion IN ('OBSERVADA', 'SUPUESTO', 'NO_APLICA')
            ),
            fuente_cotizacion TEXT,
            referencia TEXT,
            nota TEXT,
            snapshot_json TEXT NOT NULL,
            snapshot_sha256 TEXT NOT NULL CHECK (length(snapshot_sha256) = 64),
            creado_por TEXT NOT NULL CHECK (length(trim(creado_por)) > 0),
            creado_en TEXT NOT NULL,
            CHECK (
                (moneda = 'USD' AND cotizacion_ars_por_usd IS NULL
                    AND naturaleza_cotizacion = 'NO_APLICA'
                    AND fuente_cotizacion IS NULL)
                OR
                (moneda = 'ARS' AND cotizacion_ars_por_usd IS NOT NULL
                    AND CAST(cotizacion_ars_por_usd AS NUMERIC) > 0
                    AND naturaleza_cotizacion IN ('OBSERVADA', 'SUPUESTO'))
            ),
            CHECK (
                moneda = 'USD' OR naturaleza_cotizacion <> 'OBSERVADA'
                OR length(trim(coalesce(fuente_cotizacion, ''))) > 0
            )
        )
        """
    )
    db.ejecutar(
        """
        CREATE TABLE IF NOT EXISTS valuaciones_inversion_reposicion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL REFERENCES planes_reposicion(id) ON DELETE RESTRICT,
            fecha_valuacion TEXT NOT NULL,
            moneda TEXT NOT NULL CHECK (moneda IN ('ARS', 'USD')),
            valor_original TEXT NOT NULL CHECK (
                length(trim(valor_original)) > 0 AND CAST(valor_original AS NUMERIC) >= 0
            ),
            cotizacion_ars_por_usd TEXT,
            equivalente_usd TEXT NOT NULL CHECK (
                length(trim(equivalente_usd)) > 0 AND CAST(equivalente_usd AS NUMERIC) > 0
            ),
            naturaleza_cotizacion TEXT NOT NULL CHECK (
                naturaleza_cotizacion IN ('OBSERVADA', 'SUPUESTO', 'NO_APLICA')
            ),
            fuente_cotizacion TEXT,
            referencia TEXT,
            nota TEXT,
            snapshot_json TEXT NOT NULL,
            snapshot_sha256 TEXT NOT NULL CHECK (length(snapshot_sha256) = 64),
            creado_por TEXT NOT NULL CHECK (length(trim(creado_por)) > 0),
            creado_en TEXT NOT NULL,
            CHECK (
                (moneda = 'USD' AND cotizacion_ars_por_usd IS NULL
                    AND naturaleza_cotizacion = 'NO_APLICA'
                    AND fuente_cotizacion IS NULL)
                OR
                (moneda = 'ARS' AND cotizacion_ars_por_usd IS NOT NULL
                    AND CAST(cotizacion_ars_por_usd AS NUMERIC) > 0
                    AND naturaleza_cotizacion IN ('OBSERVADA', 'SUPUESTO'))
            ),
            CHECK (
                moneda = 'USD' OR naturaleza_cotizacion <> 'OBSERVADA'
                OR length(trim(coalesce(fuente_cotizacion, ''))) > 0
            )
        )
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_flujos_inversion_reposicion_fecha
        ON flujos_inversion_reposicion (plan_id, fecha_flujo, id)
        """
    )
    db.ejecutar(
        """
        CREATE INDEX IF NOT EXISTS idx_valuaciones_inversion_reposicion_fecha
        ON valuaciones_inversion_reposicion (plan_id, fecha_valuacion DESC, id DESC)
        """
    )

    for tabla, etiqueta in (
        ("flujos_inversion_reposicion", "flujos de inversión"),
        ("valuaciones_inversion_reposicion", "valuaciones de inversión"),
    ):
        base = tabla.replace("_", "")
        db.ejecutar(
            f"""
            CREATE TRIGGER IF NOT EXISTS trg_{base}_solo_plan_interno_activo
            BEFORE INSERT ON {tabla}
            WHEN COALESCE(
                (
                    SELECT estado = 'ACTIVO' AND tipo_plan = 'REPOSICION_INTERNA'
                    FROM planes_reposicion WHERE id = NEW.plan_id
                ),
                0
            ) <> 1
            BEGIN
                SELECT RAISE(ABORT, 'solo se registran movimientos de inversión en un plan interno activo');
            END
            """
        )
        db.ejecutar(
            f"""
            CREATE TRIGGER IF NOT EXISTS trg_{base}_no_update
            BEFORE UPDATE ON {tabla}
            BEGIN
                SELECT RAISE(ABORT, '{etiqueta} inmutables; registre una corrección nueva');
            END
            """
        )
        db.ejecutar(
            f"""
            CREATE TRIGGER IF NOT EXISTS trg_{base}_no_delete
            BEFORE DELETE ON {tabla}
            BEGIN
                SELECT RAISE(ABORT, '{etiqueta} se conservan como historial');
            END
            """
        )
        columna_fecha = "fecha_flujo" if tabla == "flujos_inversion_reposicion" else "fecha_valuacion"
        db.ejecutar(
            f"""
            CREATE TRIGGER IF NOT EXISTS trg_{base}_actualizar_plan
            AFTER INSERT ON {tabla}
            BEGIN
                UPDATE planes_reposicion
                SET actualizado_en = NEW.creado_en
                WHERE id = NEW.plan_id AND estado = 'ACTIVO';
            END
            """
        )
