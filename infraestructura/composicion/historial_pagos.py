"""Composición SQLite del historial auditable de pagos."""

from __future__ import annotations

from aplicacion.consultas.historial_pagos import HistorialPagosQuery
from infraestructura.consultas.historial_pagos import HistorialPagosSQLiteQuery


def crear_historial_pagos_query(db) -> HistorialPagosQuery:
    """Conecta el contrato de aplicación con el adaptador SQLite de solo lectura."""
    return HistorialPagosQuery(HistorialPagosSQLiteQuery(db))


__all__ = ["crear_historial_pagos_query"]
