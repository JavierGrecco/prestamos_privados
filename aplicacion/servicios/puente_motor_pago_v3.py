"""G6: puente de adopción gradual del Motor de Pagos V3.

Permite mantener el servicio legacy como escritura efectiva mientras V3 corre
en modo sombra, sin efectos secundarios, para medir divergencias antes de un
cut-over. En modo V3, la nueva ruta pasa a ser la efectiva.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.registro_pago_v3 import fingerprint_command
from dominio.excepciones import ErrorInvariante, ErrorValidacion


class ModoMotorPagoV3(str, Enum):
    LEGACY = "LEGACY"
    SOMBRA = "SOMBRA"
    V3 = "V3"


@dataclass(frozen=True)
class DivergenciaMotorPagoV3:
    fingerprint: str
    resumen: str

    def __post_init__(self) -> None:
        if not self.fingerprint.strip():
            raise ErrorInvariante("La divergencia debe estar asociada a una huella")
        if not self.resumen.strip():
            raise ErrorInvariante("La divergencia debe tener un resumen")


@dataclass(frozen=True)
class ResultadoPuenteMotorPagoV3:
    resultado_efectivo: Any
    plan_sombra_v3: Any | None
    divergencia: DivergenciaMotorPagoV3 | None
    error_sombra: str | None
    modo: ModoMotorPagoV3


ComparadorSombra = Callable[[Any, Any], str | None]
PlanificadorSombra = Callable[[RegistrarPagoCommand], Any]
Registrador = Callable[[RegistrarPagoCommand], Any]
ObservadorDivergencia = Callable[[DivergenciaMotorPagoV3], None]


class PuenteMotorPagoV3:
    """Selecciona el motor efectivo y opcionalmente ejecuta V3 en sombra."""

    def __init__(
        self,
        *,
        modo: ModoMotorPagoV3,
        registrar_legacy: Registrador | None = None,
        registrar_v3: Registrador | None = None,
        planificar_v3_sombra: PlanificadorSombra | None = None,
        comparar_sombra: ComparadorSombra | None = None,
        observar_divergencia: ObservadorDivergencia | None = None,
    ) -> None:
        self._modo = ModoMotorPagoV3(modo)
        self._legacy = registrar_legacy
        self._v3 = registrar_v3
        self._shadow = planificar_v3_sombra
        self._comparar = comparar_sombra
        self._observar = observar_divergencia
        self._validar_configuracion()

    def _validar_configuracion(self) -> None:
        if self._modo is ModoMotorPagoV3.LEGACY and self._legacy is None:
            raise ErrorValidacion("El modo LEGACY requiere un registrador legacy")
        if self._modo is ModoMotorPagoV3.V3 and self._v3 is None:
            raise ErrorValidacion("El modo V3 requiere un registrador V3")
        if self._modo is ModoMotorPagoV3.SOMBRA:
            if self._legacy is None:
                raise ErrorValidacion("El modo SOMBRA requiere un registrador legacy")
            if self._shadow is None:
                raise ErrorValidacion("El modo SOMBRA requiere un planificador V3 sin efectos")
            if self._comparar is None:
                raise ErrorValidacion("El modo SOMBRA requiere un comparador")

    def ejecutar(self, command: RegistrarPagoCommand) -> ResultadoPuenteMotorPagoV3:
        if self._modo is ModoMotorPagoV3.LEGACY:
            assert self._legacy is not None
            return ResultadoPuenteMotorPagoV3(
                resultado_efectivo=self._legacy(command),
                plan_sombra_v3=None,
                divergencia=None,
                error_sombra=None,
                modo=self._modo,
            )

        if self._modo is ModoMotorPagoV3.V3:
            assert self._v3 is not None
            return ResultadoPuenteMotorPagoV3(
                resultado_efectivo=self._v3(command),
                plan_sombra_v3=None,
                divergencia=None,
                error_sombra=None,
                modo=self._modo,
            )

        assert self._legacy is not None and self._shadow is not None and self._comparar is not None
        resultado_legacy = self._legacy(command)
        plan_v3 = None
        divergencia = None
        error_sombra = None
        try:
            plan_v3 = self._shadow(command)
            resumen = self._comparar(resultado_legacy, plan_v3)
            if resumen:
                divergencia = DivergenciaMotorPagoV3(
                    fingerprint=fingerprint_command(command),
                    resumen=resumen,
                )
                if self._observar is not None:
                    self._observar(divergencia)
        except Exception as exc:
            # Una falla de SOMBRA nunca debe invalidar el resultado efectivo de Legacy.
            error_sombra = f"{type(exc).__name__}: {exc}"

        return ResultadoPuenteMotorPagoV3(
            resultado_efectivo=resultado_legacy,
            plan_sombra_v3=plan_v3,
            divergencia=divergencia,
            error_sombra=error_sombra,
            modo=self._modo,
        )
