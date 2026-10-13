"""Contratos de persistencia para el registro de pagos V3.

Estas definiciones describen el intercambio entre el caso de uso de pagos y el
adaptador que persiste la operación. No dependen de SQLite ni de una implementación
concreta del servicio.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from aplicacion.comandos import RegistrarPagoCommand
from dominio.excepciones import ErrorInvariante


@dataclass(frozen=True)
class EstadoRegistroPagoV3:
    """Estado vigente que la persistencia relee dentro de la transacción crítica."""

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
    """Referencia de una operación de pago aceptada y ya persistida."""

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


class RepositorioRegistroPagoV3(Protocol):
    """Puerto que debe implementar la persistencia de un pago.

    El método `persistir_pago` participa en la transacción iniciada por el caso
    de uso y registra en una sola unidad atómica el pago, las imputaciones, las
    cuotas actualizadas, el ledger y la auditoría. Debe rechazar los conflictos
    de revisión sin dejar cambios parciales.
    """

    def begin(self) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def buscar_idempotencia(
        self, idempotency_key: str
    ) -> IdempotenciaPagoV3 | None: ...

    def obtener_estado_pago(self, prestamo_id: int) -> EstadoRegistroPagoV3: ...

    def persistir_pago(
        self,
        command: RegistrarPagoCommand,
        plan: Any,
        *,
        fingerprint: str,
        revision_esperada: int,
    ) -> int: ...
