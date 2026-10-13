"""Ensamblado de la fachada de consulta de pagos con adaptadores SQLite.

Este módulo es el límite de composición: traduce la dependencia abstracta
solicitada por aplicación a los repositorios y servicios concretos disponibles
en la distribución local.
"""

from __future__ import annotations

from aplicacion.consultas.deuda_proximo_pago import ServicioDeudaProximoPago
from aplicacion.consultas.preview_pago import ServicioPreviewPago
from aplicacion.consultas.preview_pago_v3 import ServicioPreviewPagoV3
from aplicacion.servicios.pagos_simulacion import ServicioPagosConSimulacion
from aplicacion.servicios.configuracion_motor_pago import ServicioConfiguracionMotorPago
from aplicacion.servicios.preflight_motor_pago_v3 import PreflightMotorPagoV3
from aplicacion.servicios.precheck_canary_motor_pago_v3 import ServicioReadinessCanaryV3
from aplicacion.servicios.paquete_canary_v3 import ServicioPaqueteCanaryV3
from aplicacion.servicios.operacion_ui import ServicioOperacionUI
from aplicacion.servicios.pagos import ServicioPagos
from aplicacion.servicios.registro_pago_ui import ServicioRegistroPagoUI
from aplicacion.servicios.fabrica_registro_pago_v3 import (
    crear_registrador_pago_v3_completo_con_adelantos,
)
from aplicacion.servicios.fabrica_sombra_pago_v3_sqlite import (
    crear_puente_sombra_pago_v3_sqlite,
)
from infraestructura.repositorios import PrestamoRepo, PoliticaPagoRepo
from infraestructura.repositorios.registro_pago_v3 import (
    RepositorioRegistroPagoSQLiteV3,
)
from infraestructura.migraciones import version_actual
from infraestructura.consultas.integridad_v3 import auditar_integridad_v3
from infraestructura.consultas.metricas_sombra_v3 import MetricasSombraV3Query


def _crear_servicio_preview_pago_v3(
    db,
    *,
    prestamos: PrestamoRepo,
    deuda: ServicioDeudaProximoPago,
) -> ServicioPreviewPagoV3:
    """Arma V3 compartiendo las lecturas ya resueltas por el punto de composición."""
    return ServicioPreviewPagoV3(
        prestamos=prestamos,
        politicas=PoliticaPagoRepo(db),
        estado_pago=RepositorioRegistroPagoSQLiteV3(db),
        deuda=deuda,
    )


def crear_servicio_preview_pago_v3(db) -> ServicioPreviewPagoV3:
    """Construye el preview V3 con adaptadores SQLite de solo lectura."""
    prestamos = PrestamoRepo(db)
    deuda = ServicioDeudaProximoPago(prestamos)
    return _crear_servicio_preview_pago_v3(
        db,
        prestamos=prestamos,
        deuda=deuda,
    )


def crear_servicio_preview_pago(db) -> ServicioPreviewPago:
    """Construye la fachada de preview con las implementaciones SQLite locales."""
    prestamos = PrestamoRepo(db)
    deuda = ServicioDeudaProximoPago(prestamos)
    return ServicioPreviewPago(
        deuda=deuda,
        legacy=ServicioPagosConSimulacion(db),
        v3=_crear_servicio_preview_pago_v3(
            db,
            prestamos=prestamos,
            deuda=deuda,
        ),
    )


def crear_preflight_motor_pago_v3(db, **umbrales) -> PreflightMotorPagoV3:
    """Conecta las consultas de solo lectura requeridas por el preflight V3."""
    return PreflightMotorPagoV3(
        obtener_version_schema=lambda: version_actual(db),
        auditar_integridad=lambda: auditar_integridad_v3(db),
        obtener_metricas_sombra=lambda: MetricasSombraV3Query(db).obtener(),
        **umbrales,
    )


def crear_servicio_registro_pago_ui(db) -> ServicioRegistroPagoUI:
    """Ensambla los colaboradores de lectura y escritura para la UI local.

    Los cierres mantienen la misma BaseDatos para las operaciones transaccionales;
    el caso de uso no conoce estas fábricas ni construye repositorios concretos.
    """
    prestamos = PrestamoRepo(db)
    politicas = PoliticaPagoRepo(db)

    def registrar_legacy(**kwargs):
        return ServicioPagos(db).registrar_pago(**kwargs)

    def crear_puente_sombra():
        return crear_puente_sombra_pago_v3_sqlite(db)

    def crear_registrador_v3(**kwargs):
        return crear_registrador_pago_v3_completo_con_adelantos(db, **kwargs)

    preflight = crear_preflight_motor_pago_v3(db)
    return ServicioRegistroPagoUI(
        configuracion=ServicioConfiguracionMotorPago(db, preflight=preflight),
        preflight=preflight,
        registrar_legacy=registrar_legacy,
        crear_puente_sombra=crear_puente_sombra,
        prestamos=prestamos,
        politicas_pago=politicas,
        crear_registrador_v3=crear_registrador_v3,
    )


def crear_servicio_configuracion_motor_pago(db) -> ServicioConfiguracionMotorPago:
    """Construye la configuración persistente con su gate preflight canónico."""
    preflight = crear_preflight_motor_pago_v3(db)
    return ServicioConfiguracionMotorPago(db, preflight=preflight)


def crear_servicio_readiness_canary_v3(db, **umbrales) -> ServicioReadinessCanaryV3:
    """Comparte una evaluación de preflight con la lectura del modo persistente."""
    preflight = crear_preflight_motor_pago_v3(db, **umbrales)
    configuracion = ServicioConfiguracionMotorPago(db, preflight=preflight)
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
    )


def crear_servicio_operacion_ui(db) -> ServicioOperacionUI:
    """Ensambla los lectores de preflight y métricas para la vista operativa."""
    return ServicioOperacionUI(
        db,
        preflight=crear_preflight_motor_pago_v3(db),
        obtener_metricas_sombra=lambda prestamo_id=None: MetricasSombraV3Query(
            db
        ).obtener(prestamo_id),
    )
