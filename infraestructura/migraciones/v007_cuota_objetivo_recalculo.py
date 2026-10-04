"""
Migración v007: número de cuota objetivo en el historial de recálculos.

Hasta ahora, el historial de recálculos no guardaba desde qué número
de cuota se había recalculado la tabla. Eso hacía imposible, después,
saber cuáles de las cuotas actuales fueron producto de un recálculo
por adelanto.

Agrega el campo `cuota_objetivo_numero` que guarda el número de la
cuota sobre la cual se aplicó el adelanto. Todas las cuotas con
número mayor a este fueron recreadas por el recálculo.
"""


def aplicar(db) -> None:
    db.ejecutar("""
        ALTER TABLE historial_recalculos
        ADD COLUMN cuota_objetivo_numero INTEGER NOT NULL DEFAULT 0
    """)