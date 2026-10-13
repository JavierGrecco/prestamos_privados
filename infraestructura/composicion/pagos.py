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
from infraestructura.repositorios import PrestamoRepo


def crear_servicio_preview_pago(db) -> ServicioPreviewPago:
    """Construye la fachada de preview con las implementaciones SQLite locales."""
    return ServicioPreviewPago(
        deuda=ServicioDeudaProximoPago(PrestamoRepo(db)),
        legacy=ServicioPagosConSimulacion(db),
        v3=ServicioPreviewPagoV3(db),
    )
