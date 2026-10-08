"""Migracion v015: politica de aplicacion de pagos por prestamo."""

from datetime import datetime, timezone
import json


def aplicar(db) -> None:
    db.ejecutar("""
        CREATE TABLE IF NOT EXISTS politicas_pago (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestamo_id INTEGER NOT NULL REFERENCES prestamos(id),
            version INTEGER NOT NULL,
            vigente_desde TEXT NOT NULL,
            vigente_hasta TEXT,
            estrategia_obligaciones TEXT NOT NULL,
            orden_waterfall TEXT NOT NULL,
            interes_compensatorio_post_vencimiento INTEGER NOT NULL,
            mora_habilitada INTEGER NOT NULL,
            mora_tasa_anual TEXT NOT NULL,
            mora_base TEXT NOT NULL,
            mora_convencion_dias TEXT NOT NULL,
            capitalizacion_intereses INTEGER NOT NULL,
            creado_por TEXT NOT NULL,
            creado_en TEXT NOT NULL,
            UNIQUE(prestamo_id, version)
        )
    """)

    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    orden = json.dumps(["MORA", "INTERES", "CAPITAL"])

    db.ejecutar("""
        INSERT INTO politicas_pago (
            prestamo_id, version, vigente_desde, estrategia_obligaciones,
            orden_waterfall, interes_compensatorio_post_vencimiento,
            mora_habilitada, mora_tasa_anual, mora_base,
            mora_convencion_dias, capitalizacion_intereses,
            creado_por, creado_en
        )
        SELECT
            p.id, 1, p.fecha_inicio, 'VENCIDA_MAS_ANTIGUA', ?,
            1, 1, '0.50000000', 'CUOTA_CONTRACTUAL',
            'actual_365', 0, 'migracion-v015', ?
        FROM prestamos p
        WHERE NOT EXISTS (
            SELECT 1 FROM politicas_pago pp
            WHERE pp.prestamo_id = p.id
        )
    """, (orden, ahora))

    db.ejecutar("""
        CREATE TRIGGER IF NOT EXISTS trg_prestamos_politica_pago_inicial
        AFTER INSERT ON prestamos
        BEGIN
            INSERT INTO politicas_pago (
                prestamo_id, version, vigente_desde, estrategia_obligaciones,
                orden_waterfall, interes_compensatorio_post_vencimiento,
                mora_habilitada, mora_tasa_anual, mora_base,
                mora_convencion_dias, capitalizacion_intereses,
                creado_por, creado_en
            ) VALUES (
                NEW.id, 1, NEW.fecha_inicio, 'VENCIDA_MAS_ANTIGUA',
                '[\"MORA\",\"INTERES\",\"CAPITAL\"]',
                1, 1, '0.50000000', 'CUOTA_CONTRACTUAL',
                'actual_365', 0, 'sistema', datetime('now')
            );
        END
    """)
