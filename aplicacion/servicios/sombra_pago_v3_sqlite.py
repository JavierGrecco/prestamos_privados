"""I2: adaptadores SQLite para ejecutar y comparar V3 en SOMBRA.

Este módulo no persiste nada de V3. Captura el estado económico vigente antes
de Legacy y transforma ese snapshot en un PlanPago V3 puro.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.registro_pago_v3 import EstadoRegistroPagoV3
from dominio.motor_pagos_v3 import calcular_plan_pago


CalculadorPlan = Callable[..., Any]


class SombraPagoV3SQLite:
    """Captura estado SQLite y calcula V3 únicamente sobre el snapshot."""

    def __init__(
        self,
        repositorio,
        calculador_plan: CalculadorPlan = calcular_plan_pago,
    ) -> None:
        self._repositorio = repositorio
        self._calculador = calculador_plan

    def capturar_snapshot(
        self,
        command: RegistrarPagoCommand,
    ) -> EstadoRegistroPagoV3:
        """Lee una sola vez el estado que servirá de base para V3 sombra."""
        return self._repositorio.obtener_estado_pago(command.prestamo_id)

    def planificar(
        self,
        command: RegistrarPagoCommand,
        snapshot: EstadoRegistroPagoV3,
    ) -> Any:
        """Calcula V3 sin volver a consultar SQLite."""
        if snapshot.prestamo_id != command.prestamo_id:
            raise ValueError(
                "El snapshot no corresponde al préstamo del comando"
            )

        return self._calculador(
            prestamo_id=snapshot.prestamo_id,
            fecha_valor=command.fecha_valor,
            revision_prestamo=snapshot.revision_prestamo,
            monto_recibido=command.monto,
            obligaciones=tuple(snapshot.obligaciones),
        )


def crear_sombra_pago_v3_sqlite(
    db,
    *,
    calculador_plan: CalculadorPlan = calcular_plan_pago,
) -> SombraPagoV3SQLite:
    """Construye el adaptador de SOMBRA con SQLite."""
    from infraestructura.repositorios.registro_pago_v3 import (
        RepositorioRegistroPagoSQLiteV3,
    )

    return SombraPagoV3SQLite(
        RepositorioRegistroPagoSQLiteV3(db),
        calculador_plan,
    )
