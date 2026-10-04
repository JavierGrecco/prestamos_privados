"""
Migración v004: metadata de pagos con adelantos.

Agrega columnas a `pagos` para registrar:
  - Qué tipo de pago fue (cuota, parcial, adelanto RAI/RNI).
  - Cuánto del excedente fue a capital.
  - Cuánto se ahorró en intereses.
  - Cuántas cuotas quedaban antes y después.

Y crea la tabla `historial_recalculos` que guarda cada vez que se
recalculó la tabla de amortización por un adelanto de capital.
"""


def aplicar(db) -> None:
    # -------- Columnas nuevas en pagos --------
    db.ejecutar("""
        ALTER TABLE pagos
        ADD COLUMN tipo_pago TEXT NOT NULL DEFAULT 'CUOTA'
    """)

    db.ejecutar("""
        ALTER TABLE pagos
        ADD COLUMN monto_a_capital TEXT NOT NULL DEFAULT '0'
    """)

    db.ejecutar("""
        ALTER TABLE pagos
        ADD COLUMN intereses_ahorrados TEXT NOT NULL DEFAULT '0'
    """)

    db.ejecutar("""
        ALTER TABLE pagos
        ADD COLUMN cuotas_restantes_antes INTEGER NOT NULL DEFAULT 0
    """)

    db.ejecutar("""
        ALTER TABLE pagos
        ADD COLUMN cuotas_restantes_despues INTEGER NOT NULL DEFAULT 0
    """)

    db.ejecutar("""
        ALTER TABLE pagos
        ADD COLUMN opcion_adelanto TEXT
    """)

    # -------- Tabla historial_recalculos --------
    db.ejecutar("""
        CREATE TABLE historial_recalculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestamo_id INTEGER NOT NULL REFERENCES prestamos(id)
                ON DELETE RESTRICT,
            pago_id INTEGER NOT NULL REFERENCES pagos(id)
                ON DELETE RESTRICT,
            tipo TEXT NOT NULL
                CHECK (tipo IN ('RAI', 'RNI')),
            fecha TEXT NOT NULL,
            capital_antes TEXT NOT NULL,
            capital_despues TEXT NOT NULL,
            cuotas_antes INTEGER NOT NULL,
            cuotas_despues INTEGER NOT NULL,
            intereses_antes TEXT NOT NULL,
            intereses_despues TEXT NOT NULL,
            detalle_json TEXT,
            creado_en TEXT NOT NULL
        )
    """)

    db.ejecutar("""
        CREATE INDEX idx_recalculos_prestamo
        ON historial_recalculos(prestamo_id)
    """)

    db.ejecutar("""
        CREATE INDEX idx_recalculos_pago
        ON historial_recalculos(pago_id)
    """)