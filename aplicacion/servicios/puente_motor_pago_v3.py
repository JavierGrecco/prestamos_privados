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
from aplicacion.servicios.ejecutor_sombra_pago_v3 import EjecutorSombraPagoV3
from dominio.excepciones import ErrorInvariante, ErrorValidacion


class ResultadoEjecucionSombraV3(str, Enum):
    SIN_DIVERGENCIA = "SIN_DIVERGENCIA"
    DIVERGENCIA = "DIVERGENCIA"
    ERROR_SOMBRA = "ERROR_SOMBRA"


class ModoMotorPagoV3(str, Enum):
    LEGACY = "LEGACY"
    SOMBRA = "SOMBRA"
    V3 = "V3"


@dataclass(frozen=True)
class DivergenciaMotorPagoV3:
    fingerprint: str
    resumen: str
    tipo: str = "DIVERGENCIA"
    prestamo_id: int | None = None
    pago_legacy_id: int | None = None

    def __post_init__(self) -> None:
        if not self.fingerprint.strip():
            raise ErrorInvariante("La divergencia debe estar asociada a una huella")
        if not self.resumen.strip():
            raise ErrorInvariante("La divergencia debe tener un resumen")
        if self.tipo not in {"DIVERGENCIA", "ERROR_SOMBRA"}:
            raise ErrorInvariante("Tipo de observación SOMBRA inválido")
        if self.prestamo_id is not None and self.prestamo_id <= 0:
            raise ErrorInvariante("El préstamo de la observación debe ser positivo")
        if self.pago_legacy_id is not None and self.pago_legacy_id <= 0:
            raise ErrorInvariante("El pago Legacy de la observación debe ser positivo")


@dataclass(frozen=True)
class EjecucionSombraMotorPagoV3:
    fingerprint: str
    prestamo_id: int
    pago_legacy_id: int | None
    resultado: ResultadoEjecucionSombraV3
    revision_snapshot: int | None
    resumen: str | None


@dataclass(frozen=True)
class ResultadoPuenteMotorPagoV3:
    resultado_efectivo: Any
    plan_sombra_v3: Any | None
    divergencia: DivergenciaMotorPagoV3 | None
    error_sombra: str | None
    modo: ModoMotorPagoV3
    ejecucion_sombra: EjecucionSombraMotorPagoV3 | None = None
    error_observabilidad: str | None = None


ComparadorSombra = Callable[[Any, Any], str | None]
CapturadorSnapshot = Callable[[RegistrarPagoCommand], Any]
PlanificadorSombra = Callable[[RegistrarPagoCommand, Any], Any]
Registrador = Callable[[RegistrarPagoCommand], Any]
ObservadorDivergencia = Callable[[DivergenciaMotorPagoV3], None]
ObservadorEjecucion = Callable[[EjecucionSombraMotorPagoV3], None]


class PuenteMotorPagoV3:
    """Selecciona el motor efectivo y opcionalmente ejecuta V3 en sombra."""

    def __init__(
        self,
        *,
        modo: ModoMotorPagoV3,
        registrar_legacy: Registrador | None = None,
        registrar_v3: Registrador | None = None,
        planificar_v3_sombra: PlanificadorSombra | None = None,
        capturar_snapshot: CapturadorSnapshot | None = None,
        comparar_sombra: ComparadorSombra | None = None,
        observar_divergencia: ObservadorDivergencia | None = None,
        observar_ejecucion: ObservadorEjecucion | None = None,
    ) -> None:
        self._modo = ModoMotorPagoV3(modo)
        self._legacy = registrar_legacy
        self._v3 = registrar_v3
        self._shadow = planificar_v3_sombra
        self._capturar = capturar_snapshot
        self._comparar = comparar_sombra
        self._observar = observar_divergencia
        self._observar_ejecucion = observar_ejecucion
        self._validar_configuracion()

    def _validar_configuracion(self) -> None:
        if self._modo is ModoMotorPagoV3.LEGACY and self._legacy is None:
            raise ErrorValidacion("El modo LEGACY requiere un registrador legacy")
        if self._modo is ModoMotorPagoV3.V3 and self._v3 is None:
            raise ErrorValidacion("El modo V3 requiere un registrador V3")
        if self._modo is ModoMotorPagoV3.SOMBRA:
            if self._legacy is None:
                raise ErrorValidacion("El modo SOMBRA requiere un registrador legacy")
            if self._capturar is None:
                raise ErrorValidacion("El modo SOMBRA requiere un capturador de snapshot")
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

        assert (
            self._legacy is not None
            and self._capturar is not None
            and self._shadow is not None
            and self._comparar is not None
        )

        resultado_sombra = EjecutorSombraPagoV3(
            capturar_snapshot=self._capturar,
            ejecutar_legacy=self._legacy,
            planificar_v3=self._shadow,
            comparar=self._comparar,
        ).ejecutar(command)

        pago_legacy_id = (
            resultado_sombra.resultado_legacy
            if isinstance(resultado_sombra.resultado_legacy, int)
            else None
        )
        revision_snapshot = getattr(
            resultado_sombra.snapshot_inicial,
            "revision_prestamo",
            None,
        )

        divergencia = None
        resultado_ejecucion = (
            ResultadoEjecucionSombraV3.ERROR_SOMBRA
            if resultado_sombra.error_sombra
            else (
                ResultadoEjecucionSombraV3.DIVERGENCIA
                if resultado_sombra.divergencia
                else ResultadoEjecucionSombraV3.SIN_DIVERGENCIA
            )
        )

        if resultado_sombra.divergencia:
            divergencia = DivergenciaMotorPagoV3(
                fingerprint=resultado_sombra.fingerprint,
                resumen=resultado_sombra.divergencia,
                tipo="DIVERGENCIA",
                prestamo_id=command.prestamo_id,
                pago_legacy_id=pago_legacy_id,
            )

        if resultado_sombra.error_sombra:
            divergencia_observacion = DivergenciaMotorPagoV3(
                fingerprint=resultado_sombra.fingerprint,
                resumen=resultado_sombra.error_sombra,
                tipo="ERROR_SOMBRA",
                prestamo_id=command.prestamo_id,
                pago_legacy_id=pago_legacy_id,
            )
        else:
            divergencia_observacion = divergencia

        error_sombra = resultado_sombra.error_sombra
        error_observabilidad = None
        if divergencia_observacion is not None and self._observar is not None:
            try:
                self._observar(divergencia_observacion)
            except Exception as exc:
                error_observabilidad = f"{type(exc).__name__}: {exc}"

        ejecucion = EjecucionSombraMotorPagoV3(
            fingerprint=resultado_sombra.fingerprint,
            prestamo_id=command.prestamo_id,
            pago_legacy_id=pago_legacy_id,
            resultado=resultado_ejecucion,
            revision_snapshot=revision_snapshot,
            resumen=(
                resultado_sombra.divergencia
                or resultado_sombra.error_sombra
            ),
        )

        if self._observar_ejecucion is not None:
            try:
                self._observar_ejecucion(ejecucion)
            except Exception as exc:
                nuevo_error = f"{type(exc).__name__}: {exc}"
                error_observabilidad = (
                    nuevo_error
                    if error_observabilidad is None
                    else f"{error_observabilidad} | execution observer: {nuevo_error}"
                )

        return ResultadoPuenteMotorPagoV3(
            resultado_efectivo=resultado_sombra.resultado_legacy,
            plan_sombra_v3=resultado_sombra.plan_v3,
            divergencia=divergencia,
            error_sombra=error_sombra,
            modo=self._modo,
            ejecucion_sombra=ejecucion,
            error_observabilidad=error_observabilidad,
        )
