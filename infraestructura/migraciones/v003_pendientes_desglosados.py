"""
Migración v003: desglose de pendientes por concepto.

Agrega columnas para desglosar el remanente:
  - interes_pendiente
  - capital_pendiente
  - mora_pendiente
  - fue_mora
"""


def aplicar(db) -> None:
    db.ejecutar("""
        ALTER TABLE cuotas
        ADD COLUMN interes_pendiente TEXT NOT NULL DEFAULT '0'
    """)
    db.ejecutar("""
        ALTER TABLE cuotas
        ADD COLUMN capital_pendiente TEXT NOT NULL DEFAULT '0'
    """)
    db.ejecutar("""
        ALTER TABLE cuotas
        ADD COLUMN mora_pendiente TEXT NOT NULL DEFAULT '0'
    """)
    db.ejecutar("""
        ALTER TABLE cuotas
        ADD COLUMN fue_mora INTEGER NOT NULL DEFAULT 0
    """)