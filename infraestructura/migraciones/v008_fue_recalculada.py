"""
Migración v008: flag explícito de cuota recalculada.

Cuando se aplica un adelanto, las cuotas futuras se borran y se
recrean con el nuevo plan. Hasta ahora no había forma de saber
cuáles de las cuotas actuales vienen de un recálculo.

Esta migración agrega una columna `fue_recalculada` que se setea
en True al crear una cuota desde un recálculo.
"""


def aplicar(db) -> None:
    db.ejecutar("""
        ALTER TABLE cuotas
        ADD COLUMN fue_recalculada INTEGER NOT NULL DEFAULT 0
    """)