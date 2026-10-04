"""
Migración v006: interés extra generado en pagos parciales.

Cuando un pago queda parcial, el capital pendiente genera un
interés extra en el mes siguiente. Este campo guarda ese interés
generado en el pago, para poder mostrarlo en el historial.
"""


def aplicar(db) -> None:
    db.ejecutar("""
        ALTER TABLE pagos
        ADD COLUMN interes_extra_generado TEXT NOT NULL DEFAULT '0'
    """)