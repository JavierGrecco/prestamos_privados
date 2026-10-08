"""Migración v013: configuración persistente del modo del motor de pagos."""


def aplicar(db) -> None:
    db.ejecutar(
        """
        CREATE TABLE IF NOT EXISTS configuracion_motor_pago (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            modo TEXT NOT NULL
                CHECK (modo IN ('LEGACY', 'SOMBRA', 'V3')),
            revision INTEGER NOT NULL CHECK (revision > 0),
            actualizado_en TEXT NOT NULL,
            actualizado_por TEXT NOT NULL
        )
        """
    )
    db.ejecutar(
        """
        INSERT OR IGNORE INTO configuracion_motor_pago
        (id, modo, revision, actualizado_en, actualizado_por)
        VALUES (1, 'SOMBRA', 1, datetime('now'), 'sistema')
        """
    )
