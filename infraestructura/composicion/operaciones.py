"""Composición de métricas SOMBRA y operaciones de backup/integridad."""

from __future__ import annotations

from aplicacion.servicios.metricas_sombra_v3 import ServicioMetricasSombraV3
from aplicacion.servicios.operacion_ui import ServicioOperacionUI
from infraestructura.composicion.motor_pago import crear_preflight_motor_pago_v3
from infraestructura.consultas.metricas_sombra_v3 import MetricasSombraV3Query
from infraestructura.adaptadores.operaciones_backup import OperacionesBackupSQLite


def crear_servicio_operacion_ui(db) -> ServicioOperacionUI:
    """Ensambla los lectores de preflight y métricas para la vista operativa."""
    return ServicioOperacionUI(
        db.ruta,
        preflight=crear_preflight_motor_pago_v3(db),
        obtener_metricas_sombra=lambda prestamo_id=None: MetricasSombraV3Query(
            db
        ).obtener(prestamo_id),
        operaciones_backup=OperacionesBackupSQLite(),
    )


def crear_servicio_metricas_sombra_v3(db) -> ServicioMetricasSombraV3:
    """Conecta la consulta SQLite de métricas con el caso de uso público."""
    return ServicioMetricasSombraV3(MetricasSombraV3Query(db))


__all__ = [
    "crear_servicio_operacion_ui",
    "crear_servicio_metricas_sombra_v3",
]
