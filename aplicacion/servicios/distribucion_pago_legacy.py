"""Distribución de un pago entre los inversores de un préstamo.

El colaborador convierte el importe ya imputado al pago en movimientos
proporcionales a la participación de cada inversor. No abre una transacción:
debe ejecutarse dentro de la unidad de trabajo del registro de pago para que
la distribución se confirme o revierta junto con el pago, las cuotas y la
auditoría.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal

from aplicacion.puertos.registro_pago_legacy import (
    ConsultaParticipacionesRegistroPago,
    RegistroLedgerPago,
)


class DistribuidorPagoLegacy:
    """Prepara y registra los movimientos proporcionales de los inversores."""

    def __init__(
        self,
        *,
        participaciones: ConsultaParticipacionesRegistroPago,
        ledger: RegistroLedgerPago,
    ) -> None:
        self._participaciones = participaciones
        self._ledger = ledger

    def distribuir(
        self,
        *,
        prestamo_id: int,
        aplicado: Mapping[str, Decimal],
        fecha_real: date,
        correlacion_id: str,
    ) -> None:
        """Registra el reparto en el ledger sin abrir ni confirmar transacciones."""
        partes = self._participaciones.por_prestamo(prestamo_id)
        if not partes:
            return

        monto_total = sum(aplicado.values(), Decimal("0"))
        if monto_total <= 0:
            return

        movimientos: list[dict[str, object]] = []
        for parte in partes:
            monto_inversor = monto_total * parte.porcentaje
            if monto_inversor > 0:
                movimientos.append({
                    "entidad": "INVERSOR",
                    "entidad_id": parte.inversor_id,
                    "tipo_movimiento": "COBRO_PAGO",
                    "debe": monto_inversor,
                    "haber": Decimal("0"),
                    "fecha": fecha_real,
                })
                movimientos.append({
                    "entidad": "PRESTAMO",
                    "entidad_id": prestamo_id,
                    "tipo_movimiento": "DISTRIBUCION_INVERSOR",
                    "debe": Decimal("0"),
                    "haber": monto_inversor,
                    "fecha": fecha_real,
                })

        if movimientos:
            self._ledger.registrar_operacion(
                movimientos=movimientos,
                correlacion_id=correlacion_id,
            )


__all__ = ["DistribuidorPagoLegacy"]
