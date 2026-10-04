"""
Migración v002: agregar campo `monto_pendiente` a la tabla cuotas.

Este campo guarda cuánto quedó sin pagar de una cuota cuando el
deudor pagó menos del monto total.
"""


def aplicar(db) -> None:
    db.ejecutar("""
        ALTER TABLE cuotas
        ADD COLUMN monto_pendiente TEXT NOT NULL DEFAULT '0'
    """)