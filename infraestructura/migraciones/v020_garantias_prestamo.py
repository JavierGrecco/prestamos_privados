"""Migración v020: registra garantías personales por préstamo.

La relación es descriptiva y auditable; no participa automáticamente en
cálculos de deuda, pagos, intereses ni ledger.
"""


def aplicar(db) -> None:
    db.ejecutar(
        """
        CREATE TABLE garantias_prestamo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestamo_id INTEGER NOT NULL
                REFERENCES prestamos(id) ON DELETE RESTRICT,
            garante_id INTEGER NOT NULL
                REFERENCES personas(id) ON DELETE RESTRICT,
            alcance TEXT NOT NULL
                CHECK (length(trim(alcance)) > 0),
            monto_maximo TEXT,
            moneda TEXT NOT NULL DEFAULT 'ARS'
                CHECK (moneda IN ('ARS')),
            estado TEXT NOT NULL DEFAULT 'ACTIVA'
                CHECK (estado IN ('ACTIVA', 'LIBERADA', 'ANULADA')),
            fecha_constitucion TEXT NOT NULL,
            fecha_fin TEXT,
            motivo_fin TEXT,
            creado_por TEXT NOT NULL,
            creado_en TEXT NOT NULL,
            actualizado_en TEXT NOT NULL,
            CHECK (
                (estado = 'ACTIVA' AND fecha_fin IS NULL AND motivo_fin IS NULL)
                OR
                (estado IN ('LIBERADA', 'ANULADA')
                 AND fecha_fin IS NOT NULL AND motivo_fin IS NOT NULL)
            )
        )
        """
    )
    db.ejecutar(
        """
        CREATE INDEX idx_garantias_prestamo
        ON garantias_prestamo (prestamo_id, estado, id)
        """
    )
    db.ejecutar(
        """
        CREATE INDEX idx_garantias_garante
        ON garantias_prestamo (garante_id, estado, id)
        """
    )
    db.ejecutar(
        """
        CREATE UNIQUE INDEX uq_garantia_activa_prestamo_persona
        ON garantias_prestamo (prestamo_id, garante_id)
        WHERE estado = 'ACTIVA'
        """
    )
