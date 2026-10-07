"""Preflight de imports para la integración F3.1→G7.

Este test existe para detectar incompatibilidades de símbolos base antes de
intentar ejecutar la suite financiera completa.
"""

import importlib


MODULES = (
    "dominio.distribucion_pago_v3",
    "dominio.politica_devengamiento_v3",
    "dominio.adelanto_v3",
    "infraestructura.repositorios.devengamientos_v3",
    "infraestructura.repositorios.registro_pago_v3",
    "infraestructura.repositorios.participaciones_pago_v3",
    "infraestructura.consultas.pagos_v3",
    "aplicacion.servicios.plan_pago_v3_devengamientos",
    "aplicacion.servicios.registro_pago_v3_devengamientos",
    "aplicacion.servicios.registro_pago_v3_completo",
    "aplicacion.servicios.registro_pago_v3_completo_adelantos",
    "aplicacion.servicios.fabrica_registro_pago_v3",
    "aplicacion.servicios.puente_motor_pago_v3",
    "aplicacion.consultas.pago_one_shot_v3",
)


def test_imports_f3_1_g7():
    for module in MODULES:
        importlib.import_module(module)
