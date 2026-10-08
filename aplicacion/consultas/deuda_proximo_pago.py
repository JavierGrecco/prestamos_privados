"""Consulta compartida de la deuda del próximo pago.

Esta lectura no pertenece a Legacy ni a V3: expone el estado de deuda necesario
para capturar una intención de pago sin elegir todavía una implementación de
registro.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from dominio import calcular_mora, tasa_mensual, ModalidadTasa

from infraestructura.repositorios import PrestamoRepo


class ServicioDeudaProximoPago:
    """Lee la deuda del próximo pago sin depender del servicio de registro."""

    def __init__(self, db) -> None:
        self.prestamos = PrestamoRepo(db)

    def calcular(
        self,
        prestamo_id: int,
        fecha_calculo: date,
    ) -> dict | None:
        version_id = self.prestamos.version_activa(prestamo_id)
        if version_id is None:
            return None

        info_tasa = self.prestamos.info_tasa_activa(prestamo_id)
        if info_tasa is None:
            return None

        cuotas = self.prestamos.cuotas(version_id)

        cuota_objetivo = None
        anteriores = []
        for c in cuotas:
            if c.estado == "PENDIENTE":
                cuota_objetivo = c
                break
            anteriores.append(c)

        if cuota_objetivo is None:
            return None

        arrastre_interes = sum(
            (c.interes_pendiente for c in anteriores), Decimal("0.00")
        )
        arrastre_capital = sum(
            (c.capital_pendiente for c in anteriores), Decimal("0.00")
        )
        arrastre_mora = sum(
            (c.mora_pendiente for c in anteriores), Decimal("0.00")
        )

        i_mensual = tasa_mensual(
            info_tasa["tasa_anual"],
            ModalidadTasa(info_tasa["modalidad"]),
        )
        interes_extra = (
            arrastre_capital * i_mensual
        ).quantize(Decimal("0.01"))

        mora_nueva = Decimal("0.00")
        if (
            cuota_objetivo.fecha_vencimiento
            and cuota_objetivo.fecha_vencimiento < fecha_calculo
        ):
            mora_nueva = calcular_mora(
                monto_vencido=cuota_objetivo.cuota,
                tasa_mora_anual=Decimal("0.50"),
                fecha_vencimiento=cuota_objetivo.fecha_vencimiento,
                fecha_calculo=fecha_calculo,
            )

        total_a_pagar = (
            cuota_objetivo.interes
            + cuota_objetivo.capital
            + arrastre_interes
            + arrastre_capital
            + arrastre_mora
            + interes_extra
            + mora_nueva
        )

        return {
            "cuota_objetivo": cuota_objetivo,
            "cuotas_anteriores": anteriores,
            "arrastre_interes": arrastre_interes,
            "arrastre_capital": arrastre_capital,
            "arrastre_mora": arrastre_mora,
            "interes_extra": interes_extra,
            "mora_nueva": mora_nueva,
            "cuota_interes": cuota_objetivo.interes,
            "cuota_capital": cuota_objetivo.capital,
            "total_a_pagar": total_a_pagar,
        }
