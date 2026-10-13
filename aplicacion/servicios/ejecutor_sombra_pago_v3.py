"""Ejecución segura del modo SOMBRA para pagos V3.

La clase separa explícitamente el estado inicial del estado mutado por Legacy.
La sombra recibe un snapshot inmutable y nunca escribe por sí misma.

El servicio es deliberadamente genérico: no conoce SQLite ni Streamlit y puede
usarse tanto con un snapshot de repositorio como con un DTO construido por la
capa de aplicación.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.registro_pago_v3 import fingerprint_command
from dominio.excepciones import ErrorInvariante


CapturarSnapshot = Callable[[RegistrarPagoCommand], Any]
EjecutarLegacy = Callable[[RegistrarPagoCommand], Any]
PlanificarV3 = Callable[[RegistrarPagoCommand, Any], Any]
CompararResultados = Callable[[Any, Any], str | None]
ResolverReintento = Callable[[RegistrarPagoCommand], Any | None]


@dataclass(frozen=True)
class ResultadoSombraPagoV3:
    """Resultado de Legacy + evaluación V3 sobre el estado inicial."""

    resultado_legacy: Any
    snapshot_inicial: Any
    plan_v3: Any | None
    divergencia: str | None
    error_sombra: str | None
    fingerprint: str
    es_repeticion_idempotente: bool = False

    @property
    def legacy_exitoso(self) -> bool:
        return self.resultado_legacy is not None

    @property
    def sombra_exitosa(self) -> bool:
        return self.error_sombra is None


class EjecutorSombraPagoV3:
    """Ejecuta Legacy y V3 sombra con aislamiento de efectos."""

    def __init__(
        self,
        *,
        capturar_snapshot: CapturarSnapshot,
        ejecutar_legacy: EjecutarLegacy,
        planificar_v3: PlanificarV3,
        comparar: CompararResultados,
        resolver_reintento_idempotente: ResolverReintento | None = None,
    ) -> None:
        self._capturar = capturar_snapshot
        self._legacy = ejecutar_legacy
        self._v3 = planificar_v3
        self._comparar = comparar
        self._resolver_reintento_idempotente = resolver_reintento_idempotente

    def ejecutar(self, command: RegistrarPagoCommand) -> ResultadoSombraPagoV3:
        fingerprint = fingerprint_command(command)

        # Un reintento conocido no captura un snapshot ya posterior al pago ni
        # genera una segunda comparación/observación para el mismo movimiento.
        if self._resolver_reintento_idempotente is not None:
            existente = self._resolver_reintento_idempotente(command)
            if existente is not None:
                pago_id = getattr(existente, "pago_id", existente)
                return ResultadoSombraPagoV3(
                    resultado_legacy=int(pago_id),
                    snapshot_inicial=None,
                    plan_v3=None,
                    divergencia=None,
                    error_sombra=None,
                    fingerprint=fingerprint,
                    es_repeticion_idempotente=True,
                )

        # El snapshot se toma ANTES de que Legacy pueda mutar el estado.
        snapshot = self._capturar(command)

        resultado_registro = self._legacy(command)
        repeticion_idempotente = bool(
            getattr(resultado_registro, "es_repeticion_idempotente", False)
        )
        resultado_legacy = getattr(resultado_registro, "pago_id", resultado_registro)
        if repeticion_idempotente:
            # Cierra la carrera en la que otra conexión confirmó la misma clave
            # entre el precheck y la transacción Legacy.
            return ResultadoSombraPagoV3(
                resultado_legacy=int(resultado_legacy),
                snapshot_inicial=snapshot,
                plan_v3=None,
                divergencia=None,
                error_sombra=None,
                fingerprint=fingerprint,
                es_repeticion_idempotente=True,
            )

        plan_v3 = None
        divergencia = None
        error_sombra = None

        try:
            plan_v3 = self._v3(command, snapshot)
            divergencia = self._comparar(resultado_legacy, plan_v3)
        except Exception as exc:
            # SOMBRA jamás invalida una operación Legacy exitosa.
            error_sombra = f"{type(exc).__name__}: {exc}"

        return ResultadoSombraPagoV3(
            resultado_legacy=resultado_legacy,
            snapshot_inicial=snapshot,
            plan_v3=plan_v3,
            divergencia=divergencia,
            error_sombra=error_sombra,
            fingerprint=fingerprint,
        )
