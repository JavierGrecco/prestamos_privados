"""Composición de registradores y puente SOMBRA sobre SQLite.

Estas fábricas conectan casos de uso de aplicación con adaptadores concretos.
Por eso viven en infraestructura/composicion y no en aplicacion/servicios.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable

from dominio.devengamiento_v3 import PoliticaInteres
from dominio.motor_pagos_v3 import calcular_plan_pago
from dominio.politica_pago import PoliticaImputacionPago
from dominio.politica_devengamiento_v3 import (
    PoliticaInteresCapitalPendiente,
    PoliticaMoraContractualV3,
)
from dominio.tipos import ConvencionDias, ModalidadTasa, SistemaAmortizacion
from aplicacion.servicios.puente_motor_pago_v3 import (
    ModoMotorPagoV3,
    PuenteMotorPagoV3,
)
from aplicacion.servicios.sombra_pago_v3_sqlite import SombraPagoV3SQLite
from aplicacion.servicios.pagos import ServicioPagos
from aplicacion.servicios.registro_pago_v3 import fingerprint_command
from aplicacion.servicios.registro_pago_v3 import RegistrarPagoV3
from aplicacion.servicios.registro_pago_v3_devengamientos import RegistrarPagoV3ConDevengamientos
from aplicacion.servicios.registro_pago_v3_completo import RegistrarPagoV3Completo
from aplicacion.servicios.registro_pago_v3_completo_adelantos import (
    RegistrarPagoV3CompletoConAdelantos,
)
from infraestructura.db import BaseDatos
from infraestructura.consultas.comparador_sombra_pago_v3 import (
    ComparadorSombraPagoSQLite,
)
from infraestructura.repositorios.registro_pago_v3 import (
    RepositorioRegistroPagoSQLiteV3,
)
from infraestructura.repositorios.observaciones_sombra_v3 import (
    ObservacionesSombraV3Repo,
)
from infraestructura.repositorios.ejecuciones_sombra_v3 import (
    EjecucionesSombraV3Repo,
)
from infraestructura.repositorios.politicas_pago import PoliticaPagoRepo


def _resolver_politicas_v3(
    politica_pago: PoliticaImputacionPago | None,
    *,
    tasa_anual: Decimal,
    modalidad_tasa: ModalidadTasa,
    convencion_dias: ConvencionDias,
):
    politica_pago = politica_pago or PoliticaImputacionPago.canonica()
    politica_interes = PoliticaInteresCapitalPendiente(
        PoliticaInteres(
            tasa_anual=tasa_anual,
            modalidad_tasa=modalidad_tasa,
            convencion_dias=convencion_dias,
        )
    )
    politica_mora = (
        PoliticaMoraContractualV3(
            tasa_anual=politica_pago.mora_tasa_anual,
            convencion_dias=politica_pago.mora_convencion_dias,
            base=politica_pago.mora_base,
        )
        if politica_pago.mora_habilitada
        else None
    )
    return politica_interes, politica_mora, politica_pago


def crear_registrador_pago_v3(
    db: BaseDatos,
    calculador_plan: Callable[..., Any] | None = None,
) -> RegistrarPagoV3:
    """Construye el caso de uso V3 con el adaptador SQLite."""
    repositorio = RepositorioRegistroPagoSQLiteV3(db)
    if calculador_plan is None:
        return RegistrarPagoV3(repositorio)
    return RegistrarPagoV3(repositorio, calculador_plan)


def crear_registrador_pago_v3_con_devengamientos(
    db: BaseDatos,
    *,
    tasa_anual: Decimal,
    modalidad_tasa: ModalidadTasa,
    convencion_dias: ConvencionDias,
    politica_pago: PoliticaImputacionPago | None = None,
):
    politica, politica_mora, politica_pago = _resolver_politicas_v3(
        politica_pago,
        tasa_anual=tasa_anual,
        modalidad_tasa=modalidad_tasa,
        convencion_dias=convencion_dias,
    )
    return RegistrarPagoV3ConDevengamientos(
        RepositorioRegistroPagoSQLiteV3(db),
        politica,
        politica_mora,
        politica_pago,
    )


def crear_registrador_pago_v3_completo(
    db: BaseDatos,
    *,
    tasa_anual: Decimal,
    modalidad_tasa: ModalidadTasa,
    convencion_dias: ConvencionDias,
    politica_pago: PoliticaImputacionPago | None = None,
):
    """Construye la ruta V3 con devengamientos y distribución a inversores."""
    politica, politica_mora, politica_pago = _resolver_politicas_v3(
        politica_pago,
        tasa_anual=tasa_anual,
        modalidad_tasa=modalidad_tasa,
        convencion_dias=convencion_dias,
    )
    return RegistrarPagoV3Completo(
        RepositorioRegistroPagoSQLiteV3(db),
        politica,
        politica_mora,
        politica_pago,
    )


def crear_registrador_pago_v3_completo_con_adelantos(
    db: BaseDatos,
    *,
    tasa_anual: Decimal,
    modalidad_tasa: ModalidadTasa,
    convencion_dias: ConvencionDias,
    politica_pago: PoliticaImputacionPago | None = None,
    sistema: SistemaAmortizacion | None = None,
    recalcular_rai_fn=None,
    recalcular_rni_fn=None,
):
    """Construye V3 completo con RAI/RNI y recalculación histórica."""
    politica, politica_mora, politica_pago = _resolver_politicas_v3(
        politica_pago,
        tasa_anual=tasa_anual,
        modalidad_tasa=modalidad_tasa,
        convencion_dias=convencion_dias,
    )
    return RegistrarPagoV3CompletoConAdelantos(
        RepositorioRegistroPagoSQLiteV3(db),
        politica,
        politica_mora,
        politica_pago,
        recalcular_rai_fn=recalcular_rai_fn,
        recalcular_rni_fn=recalcular_rni_fn,
        sistema=sistema or SistemaAmortizacion.FRANCES,
    )


def crear_puente_sombra_pago_v3_sqlite(
    db: BaseDatos,
    *,
    calculador_plan: Callable[..., Any] | None = None,
    comparador_sombra: Callable[[Any, Any], str | None] | None = None,
):
    """Construye el flujo Legacy + V3 SOMBRA con SQLite.

    El calculador predeterminado aplica la política vigente en la fecha de valor.
    Las funciones de escritura, idempotencia y observabilidad siguen usando la
    misma instancia de base de datos que el servicio Legacy.
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

    sombra = SombraPagoV3SQLite(
        RepositorioRegistroPagoSQLiteV3(db),
        calculador_plan=calculador_plan,
    )
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
