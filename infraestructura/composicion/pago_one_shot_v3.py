"""Composición local de la consulta One Shot de pagos V3."""

from __future__ import annotations

from aplicacion.consultas.pago_one_shot_v3 import PagoOneShotV3Query
from infraestructura.consultas.pagos_v3 import ConsultaPagoV3SQLite


def crear_consulta_pago_one_shot_v3(db) -> PagoOneShotV3Query:
    """Conecta la proyección de aplicación con el lector auditable SQLite."""
    return PagoOneShotV3Query(ConsultaPagoV3SQLite(db))


__all__ = ["crear_consulta_pago_one_shot_v3"]
