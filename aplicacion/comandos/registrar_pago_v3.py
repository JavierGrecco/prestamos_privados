"""Command inmutable para registrar un pago.

No contiene reglas financieras ni acceso a infraestructura. Representa la
intención operacional de registrar un pago antes de entrar en la transacción.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from dominio.excepciones import ErrorValidacion
from dominio.tipos import money


@dataclass(frozen=True)
class RegistrarPagoCommand:
    """Intención operacional, separada de la decisión financiera PlanPago."""

    prestamo_id: int
    monto: Decimal
    fecha_real: date
    usuario: str
    fecha_valor: date | None = None
    medio: str | None = None
    referencia: str | None = None
    nota: str | None = None
    opcion_adelanto: str | None = None
    idempotency_key: str | None = None
    revision_prestamo: int | None = None

    def __post_init__(self) -> None:
        if self.prestamo_id <= 0:
            raise ErrorValidacion("El préstamo debe tener un ID positivo")

        monto = money(self.monto)
        if monto <= Decimal("0.00"):
            raise ErrorValidacion("El monto del pago debe ser mayor a cero")
        object.__setattr__(self, "monto", monto)

        if not isinstance(self.fecha_real, date):
            raise ErrorValidacion("fecha_real debe ser una fecha válida")

        usuario = self.usuario.strip()
        if not usuario:
            raise ErrorValidacion("El usuario es obligatorio")
        object.__setattr__(self, "usuario", usuario)

        fecha_valor = self.fecha_real if self.fecha_valor is None else self.fecha_valor
        if not isinstance(fecha_valor, date):
            raise ErrorValidacion("fecha_valor debe ser una fecha válida")
        object.__setattr__(self, "fecha_valor", fecha_valor)

        for nombre in ("medio", "referencia", "nota", "opcion_adelanto"):
            valor = getattr(self, nombre)
            if isinstance(valor, str):
                valor = valor.strip() or None
                object.__setattr__(self, nombre, valor)

        if self.opcion_adelanto not in (None, "RAI", "RNI"):
            raise ErrorValidacion("opcion_adelanto debe ser RAI, RNI o None")

        key = self.idempotency_key
        if key is not None:
            if not isinstance(key, str):
                raise ErrorValidacion("idempotency_key debe ser texto")
            key = key.strip()
            if not key:
                raise ErrorValidacion("idempotency_key no puede ser vacío")
            if len(key) > 255:
                raise ErrorValidacion("idempotency_key no puede superar 255 caracteres")
            object.__setattr__(self, "idempotency_key", key)

        if self.revision_prestamo is not None and self.revision_prestamo < 0:
            raise ErrorValidacion("La revisión del préstamo no puede ser negativa")
