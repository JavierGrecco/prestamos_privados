"""Composición del preflight, configuración y readiness del Motor V3."""

from __future__ import annotations

from aplicacion.servicios.configuracion_motor_pago import ServicioConfiguracionMotorPago
from aplicacion.servicios.preflight_motor_pago_v3 import PreflightMotorPagoV3
from aplicacion.servicios.precheck_canary_motor_pago_v3 import ServicioReadinessCanaryV3
from aplicacion.servicios.paquete_canary_v3 import ServicioPaqueteCanaryV3
from infraestructura.migraciones import version_actual
from infraestructura.consultas.integridad_v3 import auditar_integridad_v3
from infraestructura.consultas.metricas_sombra_v3 import MetricasSombraV3Query
from infraestructura.adaptadores.configuracion_motor_pago import ConfiguracionMotorPagoSQLite
from infraestructura.adaptadores.operaciones_backup import OperacionesBackupSQLite


def crear_preflight_motor_pago_v3(db, **umbrales) -> PreflightMotorPagoV3:
    """Conecta las consultas de solo lectura requeridas por el preflight V3."""
    return PreflightMotorPagoV3(
        obtener_version_schema=lambda: version_actual(db),
        auditar_integridad=lambda: auditar_integridad_v3(db),
        obtener_metricas_sombra=lambda: MetricasSombraV3Query(db).obtener(),
        **umbrales,
    )


def crear_servicio_configuracion_motor_pago(
    db,
    *,
    preflight: PreflightMotorPagoV3 | None = None,
) -> ServicioConfiguracionMotorPago:
    """Construye configuración, adaptador transaccional y gate preflight."""
    gate = preflight if preflight is not None else crear_preflight_motor_pago_v3(db)
    return ServicioConfiguracionMotorPago(
        persistencia=ConfiguracionMotorPagoSQLite(db),
        preflight=gate,
    )


def crear_servicio_readiness_canary_v3(db, **umbrales) -> ServicioReadinessCanaryV3:
    """Comparte una evaluación de preflight con la lectura del modo persistente."""
    preflight = crear_preflight_motor_pago_v3(db, **umbrales)
    configuracion = crear_servicio_configuracion_motor_pago(db, preflight=preflight)
    return ServicioReadinessCanaryV3(
        preflight=preflight,
        configuracion=configuracion,
    )


def crear_servicio_paquete_canary_v3(db) -> ServicioPaqueteCanaryV3:
    """Ensambla el paquete de decisión y su readiness sobre la misma base."""
    return ServicioPaqueteCanaryV3(
        evaluar_readiness=lambda **umbrales: crear_servicio_readiness_canary_v3(
            db,
            **umbrales,
        ).evaluar(),
        operaciones_backup=OperacionesBackupSQLite(),
    )


__all__ = [
    "crear_preflight_motor_pago_v3",
    "crear_servicio_configuracion_motor_pago",
    "crear_servicio_readiness_canary_v3",
    "crear_servicio_paquete_canary_v3",
]
