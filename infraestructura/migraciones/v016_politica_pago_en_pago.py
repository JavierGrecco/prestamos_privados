"""Migracion v016: conserva la politica exacta utilizada por cada pago.

Los pagos historicos se vinculan con la version de politica vigente en su
fecha_valor. Los pagos nuevos deben persistir siempre la referencia a la
politica que determinó su imputacion.
"""


def aplicar(db) -> None:
    db.ejecutar(
        "ALTER TABLE pagos ADD COLUMN politica_pago_id INTEGER REFERENCES politicas_pago(id)"
    )
    db.ejecutar(
        "CREATE INDEX IF NOT EXISTS idx_pagos_politica_pago_id "
        "ON pagos(politica_pago_id)"
    )

    # Backfill deterministico. Si una base historica no tiene una politica
    # disponible para esa fecha, se deja NULL para no inventar evidencia.
    db.ejecutar(
        """
        UPDATE pagos
        SET politica_pago_id = (
            SELECT pp.id
            FROM politicas_pago pp
            WHERE pp.prestamo_id = pagos.prestamo_id
              AND pp.vigente_desde <= pagos.fecha_valor
              AND (pp.vigente_hasta IS NULL OR pp.vigente_hasta > pagos.fecha_valor)
            ORDER BY pp.version DESC, pp.id DESC
            LIMIT 1
        )
        WHERE politica_pago_id IS NULL
        """
    )
