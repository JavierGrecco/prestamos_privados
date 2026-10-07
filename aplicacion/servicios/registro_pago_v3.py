"""V3-F.2: frontera de registro transaccional del motor de pagos.

Esta capa orquesta el registro, pero no sabe cómo persistir SQLite ni cómo
mutar cuotas. Su responsabilidad es garantizar el orden correcto:

    comando -> BEGIN -> idempotencia -> relectura vigente -> revisión ->
    cálculo PlanPago -> persistencia atómica -> COMMIT

Ante cualquier error se ejecuta ROLLBACK.

La persistencia concreta se inyecta mediante un puerto para que la migración
del servicio productivo pueda hacerse sin mezclar infraestructura y reglas
financieras.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
import hashlib
import json
from typing import Any, Callable, Protocol, Sequence

from aplicacion.comandos import RegistrarPagoCommand
from dominio.excepciones import ErrorInvariante


@dataclass(frozen=True)
class EstadoRegistroPagoV3:
    """Estado materializado releído dentro de la transacción crítica."""

    prestamo_id: int
    revision_prestamo: int
    obligaciones: Sequence[Any]

    def __post_init__(self) -> None:
        if self.prestamo_id <= 0:
            raise ErrorInvariante("El préstamo debe tener un ID positivo")
        if self.revision_prestamo < 0:
            raise ErrorInvariante("La revisión del préstamo no puede ser negativa")
        object.__setattr__(self, "obligaciones", tuple(self.obligaciones))


@dataclass(frozen=True)
class IdempotenciaPagoV3:
    """Registro persistido de una operación ya aceptada."""

    idempotency_key: str
    fingerprint: str
    pago_id: int

    def __post_init__(self) -> None:
        if not self.idempotency_key.strip():
            raise ErrorInvariante("La clave de idempotencia no puede ser vacía")
        if not self.fingerprint.strip():
            raise ErrorInvariante("El fingerprint de idempotencia no puede ser vacío")
        if self.pago_id <= 0:
            raise ErrorInvariante("El pago_id persistido debe ser positivo")


@dataclass(frozen=True)
class ResultadoRegistroPagoV3:
    pago_id: int
    revision_utilizada: int | None
    es_repeticion_idempotente: bool
    fingerprint: str
    plan: Any | None


class RepositorioRegistroPagoV3(Protocol):
    """Puerto mínimo que la infraestructura debe implementar.

    El método ``persistir_pago`` debe ejecutar, dentro de la transacción ya
    abierta por ``begin``, el pago, sus imputaciones por cuota/concepto, el
    estado materializado de las cuotas, ledger, auditoría y la actualización
    de revisión. Debe rechazar un conflicto de revisión de forma atómica.
    """

    def begin(self) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def buscar_idempotencia(self, idempotency_key: str) -> IdempotenciaPagoV3 | None: ...

    def obtener_estado_pago(self, prestamo_id: int) -> EstadoRegistroPagoV3: ...

    def persistir_pago(
        self,
        command: RegistrarPagoCommand,
        plan: Any,
        *,
        fingerprint: str,
        revision_esperada: int,
    ) -> int: ...


CalculadorPlanV3 = Callable[..., Any]


def fingerprint_command(command: RegistrarPagoCommand) -> str:
    """Calcula una huella estable del contenido financiero/operacional.

    La clave de idempotencia queda fuera de la huella para detectar de forma
    explícita el caso "misma clave, payload diferente".
    """
    valores = asdict(command)
    valores.pop("idempotency_key", None)

    for clave, valor in valores.items():
        if isinstance(valor, Decimal):
            valores[clave] = format(valor, "f")
        elif isinstance(valor, date):
            valores[clave] = valor.isoformat()

    serializado = json.dumps(
        valores,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(serializado).hexdigest()


def _calculador_plan_por_defecto(**kwargs: Any) -> Any:
    """Carga perezosamente el motor V3 para conservar la frontera testeable."""
    from dominio.motor_pagos_v3 import calcular_plan_pago

    return calcular_plan_pago(**kwargs)


class RegistrarPagoV3:
    """Orquestador transaccional, independiente de SQLite y de Streamlit."""

    def __init__(
        self,
        repositorio: RepositorioRegistroPagoV3,
        calculador_plan: CalculadorPlanV3 = _calculador_plan_por_defecto,
    ) -> None:
        self._repositorio = repositorio
        self._calculador_plan = calculador_plan

    def ejecutar(self, command: RegistrarPagoCommand) -> ResultadoRegistroPagoV3:
        """Ejecuta el registro contra el estado vigente y de forma atómica."""
        fingerprint = fingerprint_command(command)
        self._repositorio.begin()
        try:
            if command.idempotency_key:
                existente = self._repositorio.buscar_idempotencia(command.idempotency_key)
                if existente is not None:
                    if existente.fingerprint != fingerprint:
                        raise ErrorInvariante(
                            "La idempotency_key ya fue utilizada con un payload diferente"
                        )
                    self._repositorio.commit()
                    return ResultadoRegistroPagoV3(
                        pago_id=existente.pago_id,
                        revision_utilizada=None,
                        es_repeticion_idempotente=True,
                        fingerprint=fingerprint,
                        plan=None,
                    )

            estado = self._repositorio.obtener_estado_pago(command.prestamo_id)
            if estado.prestamo_id != command.prestamo_id:
                raise ErrorInvariante(
                    "El estado releído no corresponde al préstamo solicitado"
                )

            revision_esperada = (
                estado.revision_prestamo
                if command.revision_prestamo is None
                else command.revision_prestamo
            )
            if revision_esperada != estado.revision_prestamo:
                raise ErrorInvariante(
                    "Conflicto de revisión del préstamo: el estado cambió antes de registrar"
                )

            plan = self._calculador_plan(
                prestamo_id=command.prestamo_id,
                fecha_valor=command.fecha_valor,
                revision_prestamo=estado.revision_prestamo,
                monto_recibido=command.monto,
                obligaciones=tuple(estado.obligaciones),
            )

            pago_id = self._repositorio.persistir_pago(
                command,
                plan,
                fingerprint=fingerprint,
                revision_esperada=estado.revision_prestamo,
            )
            if pago_id <= 0:
                raise ErrorInvariante("La persistencia devolvió un pago_id inválido")

            self._repositorio.commit()
            return ResultadoRegistroPagoV3(
                pago_id=pago_id,
                revision_utilizada=estado.revision_prestamo,
                es_repeticion_idempotente=False,
                fingerprint=fingerprint,
                plan=plan,
            )
        except Exception:
            self._repositorio.rollback()
            raise
