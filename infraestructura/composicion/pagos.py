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
from infraestructura.repositorios import PrestamoRepo, PoliticaPagoRepo
from infraestructura.repositorios.registro_pago_v3 import (
    RepositorioRegistroPagoSQLiteV3,
)


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
