"""Factory for the real SQLite SOMBRA flow."""

from __future__ import annotations

from typing import Any, Callable

from dominio.motor_pagos_v3 import calcular_plan_pago

from aplicacion.servicios.puente_motor_pago_v3 import (
    ModoMotorPagoV3,
    PuenteMotorPagoV3,
)
from aplicacion.servicios.sombra_pago_v3_sqlite import crear_sombra_pago_v3_sqlite
from aplicacion.servicios.pagos import ServicioPagos
from aplicacion.servicios.registro_pago_v3 import fingerprint_command
from infraestructura.consultas.comparador_sombra_pago_v3 import (
    ComparadorSombraPagoSQLite,
)
from infraestructura.repositorios.observaciones_sombra_v3 import (
    ObservacionesSombraV3Repo,
)
from infraestructura.repositorios.ejecuciones_sombra_v3 import (
    EjecucionesSombraV3Repo,
)
from infraestructura.repositorios.politicas_pago import PoliticaPagoRepo


def crear_puente_sombra_pago_v3_sqlite(
    db,
    *,
    calculador_plan: Callable[..., Any] | None = None,
    comparador_sombra: Callable[[Any, Any], str | None] | None = None,
):
    """Builds the non-blocking Legacy + V3 shadow flow over one SQLite DB.

    The default shadow calculator resolves the policy version active at
    ``fecha_valor`` and passes its waterfall to the pure V3 motor. A custom
    calculator remains available for tests and controlled experiments.
    """
    if calculador_plan is None:

        def calculador_plan_con_politica(**kwargs):
            politica = PoliticaPagoRepo(db).obtener_vigente(
                kwargs["prestamo_id"],
                kwargs["fecha_valor"],
            )
            return calcular_plan_pago(
                **kwargs,
                orden_waterfall=politica.orden_waterfall,
            )

        calculador_plan = calculador_plan_con_politica

    sombra = crear_sombra_pago_v3_sqlite(db, calculador_plan=calculador_plan)
    comparador = comparador_sombra or ComparadorSombraPagoSQLite(db).comparar
    observaciones = ObservacionesSombraV3Repo(db)
    ejecuciones = EjecucionesSombraV3Repo(db)
    legacy = ServicioPagos(db)

    def huella_idempotencia(command):
        return (
            fingerprint_command(command)
            if command.idempotency_key is not None
            else None
        )

    def resolver_reintento_idempotente(command):
        return legacy.buscar_reintento_idempotente(
            idempotency_key=command.idempotency_key,
            idempotency_fingerprint=huella_idempotencia(command),
        )

    def registrar_legacy(command):
        return legacy.registrar_pago(
            prestamo_id=command.prestamo_id,
            monto=command.monto,
            fecha_real=command.fecha_real,
            usuario=command.usuario,
            medio=command.medio,
            referencia=command.referencia,
            nota=command.nota,
            opcion_adelanto=command.opcion_adelanto,
            idempotency_key=command.idempotency_key,
            idempotency_fingerprint=huella_idempotencia(command),
            devolver_resultado=True,
        )

    return PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.SOMBRA,
        registrar_legacy=registrar_legacy,
        resolver_reintento_idempotente=resolver_reintento_idempotente,
        capturar_snapshot=sombra.capturar_snapshot,
        planificar_v3_sombra=sombra.planificar,
        comparar_sombra=comparador,
        observar_divergencia=observaciones.registrar,
        observar_ejecucion=ejecuciones.registrar,
    )
