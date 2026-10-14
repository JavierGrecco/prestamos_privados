"""Composición de los colaboradores de escritura del registro de pagos UI."""

from __future__ import annotations

from infraestructura.composicion.servicio_pagos_legacy import crear_servicio_pagos_legacy
from aplicacion.servicios.registro_pago_ui import ServicioRegistroPagoUI
from infraestructura.composicion.motor_pago import (
    crear_preflight_motor_pago_v3,
    crear_servicio_configuracion_motor_pago,
)
from infraestructura.composicion.registradores_pago import (
    crear_registrador_pago_v3_completo_con_adelantos,
    crear_puente_sombra_pago_v3_sqlite,
)
from infraestructura.repositorios import PrestamoRepo, PoliticaPagoRepo


def crear_servicio_registro_pago_ui(db) -> ServicioRegistroPagoUI:
    """Ensamla los colaboradores de lectura y escritura para la UI local.

    Los cierres mantienen la misma BaseDatos para las operaciones transaccionales;
    el caso de uso no conoce estas fábricas ni construye repositorios concretos.
    """
    prestamos = PrestamoRepo(db)
    politicas = PoliticaPagoRepo(db)

    def registrar_legacy(**kwargs):
        return crear_servicio_pagos_legacy(db).registrar_pago(**kwargs)

    def crear_puente_sombra():
        return crear_puente_sombra_pago_v3_sqlite(db)

    def crear_registrador_v3(**kwargs):
        return crear_registrador_pago_v3_completo_con_adelantos(db, **kwargs)

    preflight = crear_preflight_motor_pago_v3(db)
    return ServicioRegistroPagoUI(
        configuracion=crear_servicio_configuracion_motor_pago(db, preflight=preflight),
        preflight=preflight,
        registrar_legacy=registrar_legacy,
        crear_puente_sombra=crear_puente_sombra,
        prestamos=prestamos,
        politicas_pago=politicas,
        crear_registrador_v3=crear_registrador_v3,
    )


__all__ = ["crear_servicio_registro_pago_ui"]
