"""
Migración v005: flag de pago parcial en cuotas.

Agrega un campo `tuvo_pago_parcial` que marca si la cuota en algún
momento tuvo un pago parcial, incluso si después se completó.

Esto permite mostrar en la UI "pagada con pago parcial previo"
sin perder el registro histórico.
"""


def aplicar(db) -> None:
    db.ejecutar("""
        ALTER TABLE cuotas
        ADD COLUMN tuvo_pago_parcial INTEGER NOT NULL DEFAULT 0
    """)