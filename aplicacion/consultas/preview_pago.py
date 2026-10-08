"""Fachada única de preview para la UI de pagos.

La UI consume esta interfaz y no necesita conocer si el modo vigente usa la
ruta histórica o el preview canónico V3.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from aplicacion.consultas.preview_pago_v3 import (
    PreviewPagoV3,
    ServicioPreviewPagoV3,
)
from aplicacion.servicios.pagos_simulacion import ServicioPagosConSimulacion
from aplicacion.servicios.puente_motor_pago_v3 import ModoMotorPagoV3


class ServicioPreviewPago:
    """Única entrada de aplicación para consultar el preview de un pago."""

    def __init__(self, db) -> None:
        self._legacy = ServicioPagosConSimulacion(db)
        self._v3 = ServicioPreviewPagoV3(db)

    def calcular_deuda_proximo_pago(
        self,
        prestamo_id: int,
        fecha_calculo: date,
    ) -> dict | None:
        """Obtiene el estado de deuda usado para la captura de intención."""
        return self._legacy.calcular_deuda_proximo_pago(
            prestamo_id,
            fecha_calculo,
        )

    def simular_pago_legacy(
        self,
        prestamo_id: int,
        monto: Decimal,
        fecha_calculo: date,
    ) -> dict:
        """Mantiene explícita la ruta histórica durante la transición."""
        return self._legacy.simular_pago(
            prestamo_id,
            monto,
            fecha_calculo,
        )

    def simular_adelanto(
        self,
        prestamo_id: int,
        monto_adelanto: Decimal,
        fecha_calculo: date,
    ) -> dict | None:
        return self._legacy.simular_adelanto(
            prestamo_id,
            monto_adelanto,
            fecha_calculo,
        )

    def previsualizar_v3(
        self,
        *,
        prestamo_id: int,
        monto: Decimal,
        fecha_valor: date,
        opcion_adelanto: str | None = None,
    ) -> PreviewPagoV3:
        """Construye el preview canónico V3 sin persistir."""
        return self._v3.previsualizar(
            prestamo_id=prestamo_id,
            monto=monto,
            fecha_valor=fecha_valor,
            opcion_adelanto=opcion_adelanto,
            comparar_legacy=True,
        )

    def previsualizar_por_modo(
        self,
        *,
        modo: ModoMotorPagoV3,
        prestamo_id: int,
        monto: Decimal,
        fecha_real: date,
        fecha_valor: date,
        opcion_adelanto: str | None = None,
    ) -> dict | PreviewPagoV3:
        """Selecciona la autoridad de preview sin exponerla a la UI."""
        if modo is ModoMotorPagoV3.LEGACY:
            return self.simular_pago_legacy(
                prestamo_id,
                monto,
                fecha_real,
            )
        return self.previsualizar_v3(
            prestamo_id=prestamo_id,
            monto=monto,
            fecha_valor=fecha_valor,
            opcion_adelanto=opcion_adelanto,
        )
