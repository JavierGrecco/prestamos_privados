"""Fachada pública de composición para la instalación local de pagos.

Los ensamblados detallados viven en módulos cohesionados por responsabilidad.
Este módulo conserva las rutas de importación estables que consume la UI y las
CLI mientras permite evolucionar la composición interna de forma incremental.
"""

from infraestructura.composicion.preview_pagos import (
    crear_servicio_preview_pago,
    crear_servicio_preview_pago_v3,
)
from infraestructura.composicion.motor_pago import (
    crear_preflight_motor_pago_v3,
    crear_servicio_configuracion_motor_pago,
    crear_servicio_readiness_canary_v3,
    crear_servicio_paquete_canary_v3,
)
from infraestructura.composicion.registro_pago import crear_servicio_registro_pago_ui
from infraestructura.composicion.pago_one_shot_v3 import crear_consulta_pago_one_shot_v3
from infraestructura.composicion.operaciones import (
    crear_servicio_operacion_ui,
    crear_servicio_metricas_sombra_v3,
)


__all__ = [
    "crear_servicio_preview_pago",
    "crear_servicio_preview_pago_v3",
    "crear_preflight_motor_pago_v3",
    "crear_servicio_registro_pago_ui",
    "crear_servicio_configuracion_motor_pago",
    "crear_servicio_readiness_canary_v3",
    "crear_servicio_paquete_canary_v3",
    "crear_servicio_operacion_ui",
    "crear_servicio_metricas_sombra_v3",
    "crear_consulta_pago_one_shot_v3",
]
