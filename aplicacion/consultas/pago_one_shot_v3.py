"""G7: proyección One Shot de un pago V3.

Es un read model orientado a UI/reportes: consume la consulta auditable y no
realiza cálculos financieros ni escrituras.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from infraestructura.consultas.pagos_v3 import PagoV3Read, obtener_pago_v3

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class PagoOneShotV3:
    pago_id: int
    prestamo_id: int
    fecha_valor: str
    monto: Decimal
    tipo_pago: str
    capital_aplicado: Decimal
    interes_aplicado: Decimal
    mora_aplicada: Decimal
    prepago: Decimal
    intereses_ahorrados: Decimal
    cuotas_restantes_antes: int
    cuotas_restantes_despues: int
    inversores_distribuidos: Decimal
    cantidad_imputaciones: int
    motor_version: str
    reconciliado: bool

    @property
    def tiene_prepago(self) -> bool:
        return self.prepago > ZERO


def proyectar_one_shot(pago: PagoV3Read) -> PagoOneShotV3:
    """Construye la proyección sin consultar ni modificar infraestructura."""
    capital = _sumar_concepto(pago, "CAPITAL")
    interes = _sumar_concepto(pago, "INTERES")
    mora = _sumar_concepto(pago, "MORA")
    prepago = sum(
        (x.monto for x in pago.imputaciones if x.origen == "PREPAGO" and x.concepto == "CAPITAL"),
        ZERO,
    )
    return PagoOneShotV3(
        pago_id=pago.pago_id,
        prestamo_id=pago.prestamo_id,
        fecha_valor=pago.fecha_valor,
        monto=pago.monto,
        tipo_pago=pago.tipo_pago,
        capital_aplicado=capital,
        interes_aplicado=interes,
        mora_aplicada=mora,
        prepago=prepago,
        intereses_ahorrados=pago.intereses_ahorrados,
        cuotas_restantes_antes=pago.cuotas_restantes_antes,
        cuotas_restantes_despues=pago.cuotas_restantes_despues,
        inversores_distribuidos=pago.reconciliacion.suma_distribucion_inversores,
        cantidad_imputaciones=len(pago.imputaciones),
        motor_version=pago.motor_version,
        reconciliado=pago.reconciliacion.integra,
    )


def obtener_one_shot_pago_v3(db, pago_id: int) -> PagoOneShotV3:
    return proyectar_one_shot(obtener_pago_v3(db, pago_id))


def _sumar_concepto(pago: PagoV3Read, concepto: str) -> Decimal:
    total = sum(
        (x.monto for x in pago.imputaciones if x.concepto == concepto),
        ZERO,
    )
    return total.quantize(Decimal("0.01"))
