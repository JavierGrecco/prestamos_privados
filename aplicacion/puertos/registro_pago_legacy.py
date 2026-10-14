"""Contratos de aplicación para registrar un pago Legacy de forma atómica."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from datetime import date
from decimal import Decimal
from typing import Any, Protocol

from dominio.politica_pago import PoliticaImputacionPago


class UnidadTrabajoRegistroPago(Protocol):
    """Delimita la unidad atómica de un registro de pago."""
    def transaccion(self, *, inmediata: bool = False) -> AbstractContextManager[Any]: ...


class RepositorioPrestamosRegistroPago(Protocol):
    """Lecturas y cambios de cuotas requeridos por el registro Legacy."""
    def obtener(self, prestamo_id: int) -> Any | None: ...
    def info_tasa_activa(self, prestamo_id: int) -> Any | None: ...
    def version_activa(self, prestamo_id: int) -> int | None: ...
    def cuotas(self, version_id: int | None) -> Sequence[Any]: ...
    def actualizar_cuota(self, **kwargs: Any) -> None: ...
    def borrar_cuotas_pendientes_desde(self, version_id: int, numero_inicio: int) -> None: ...
    def crear_cuota_individual(self, **kwargs: Any) -> int: ...


class RepositorioPagosRegistroPago(Protocol):
    """Escrituras del pago y metadatos de adelanto."""
    def registrar(
        self, prestamo_id: int, fecha_real: date, monto_moneda_pago: Decimal,
        imputaciones: list[dict[str, Any]], fecha_valor: date | None = None,
        medio: str | None = None, referencia: str | None = None,
        nota: str | None = None, tc_aplicado: Decimal | None = None,
        monto_usd_ref: Decimal | None = None, creado_por: str | None = None,
        tipo_pago: str = "CUOTA", monto_a_capital: Decimal = Decimal("0.00"),
        intereses_ahorrados: Decimal = Decimal("0.00"),
        interes_extra_generado: Decimal = Decimal("0.00"),
        cuotas_restantes_antes: int = 0, cuotas_restantes_despues: int = 0,
        opcion_adelanto: str | None = None, politica_pago_id: int | None = None,
        idempotency_key: str | None = None,
        idempotency_fingerprint: str | None = None,
    ) -> int: ...
    def actualizar_datos_adelanto(
        self, *, pago_id: int, intereses_ahorrados: Decimal,
        cuotas_restantes_despues: int, opcion_adelanto: str,
    ) -> None: ...


class ConsultaParticipacionesRegistroPago(Protocol):
    def por_prestamo(self, prestamo_id: int) -> Sequence[Any]: ...


class RegistroLedgerPago(Protocol):
    def registrar_operacion(
        self, *, movimientos: list[dict[str, Any]], correlacion_id: str
    ) -> Any: ...


class RegistroAuditoriaPago(Protocol):
    def registrar(self, **kwargs: Any) -> Any: ...


class RegistroRecalculosPago(Protocol):
    def registrar(self, **kwargs: Any) -> int: ...


class RepositorioPoliticasPago(Protocol):
    def obtener_vigente_con_id_o_canonica(
        self, prestamo_id: int, fecha: date
    ) -> tuple[int | None, PoliticaImputacionPago]: ...


class CalculadorDeudaProximoPago(Protocol):
    def __call__(
        self, prestamo_id: int, fecha_calculo: date, *,
        politica: PoliticaImputacionPago | None = None,
    ) -> dict[str, Any] | None: ...


GeneradorCorrelacionPago = Callable[[], str]

__all__ = [
    "UnidadTrabajoRegistroPago", "RepositorioPrestamosRegistroPago",
    "RepositorioPagosRegistroPago", "ConsultaParticipacionesRegistroPago",
    "RegistroLedgerPago", "RegistroAuditoriaPago", "RegistroRecalculosPago",
    "RepositorioPoliticasPago", "CalculadorDeudaProximoPago",
    "GeneradorCorrelacionPago",
]
