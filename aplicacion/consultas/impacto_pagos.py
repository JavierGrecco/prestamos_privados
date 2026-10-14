"""Proyecciones de solo lectura sobre el impacto de las decisiones de pago.

Esta consulta reúne información histórica de cuotas y pagos para presentar
costos, ahorros e hitos de forma entendible. No registra pagos ni recalcula
obligaciones financieras.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from aplicacion.puertos.impacto_pagos import (
    ConsultaCuotasImpactoPago,
    ConsultaPagosImpactoPago,
)


class ConsultaImpactoPagos:
    """Calcula resúmenes e hitos legibles a partir de lectores por contrato."""

    def __init__(
        self,
        cuotas: ConsultaCuotasImpactoPago,
        pagos: ConsultaPagosImpactoPago,
    ) -> None:
        self._cuotas = cuotas
        self._pagos = pagos

    def resumen_impacto_financiero(self, prestamo_id: int) -> dict:
        """Resume mora, costos, ahorros y cuotas con atraso de un préstamo."""
        version_id = self._cuotas.version_activa(prestamo_id)
        if version_id is None:
            return self._resumen_vacio()

        cuotas = self._cuotas.cuotas(version_id)
        pagos = self._pagos.por_prestamo(prestamo_id)
        pagos_validos = [pago for pago in pagos if pago.estado == "VALIDA"]

        interes_extra_generado = sum(
            (pago.interes_extra_generado for pago in pagos_validos),
            Decimal("0.00"),
        )
        mora_generada = sum(
            (cuota.mora_pendiente for cuota in cuotas),
            Decimal("0.00"),
        )
        intereses_ahorrados = sum(
            (pago.intereses_ahorrados for pago in pagos_validos),
            Decimal("0.00"),
        )
        capital_adelantado = sum(
            (pago.monto_a_capital for pago in pagos_validos),
            Decimal("0.00"),
        )
        numeros_con_atraso = [
            cuota.numero for cuota in cuotas if cuota.fue_mora
        ]

        costos_totales = interes_extra_generado + mora_generada
        ahorros_totales = intereses_ahorrados
        balance = costos_totales - ahorros_totales

        return {
            "mora_pendiente": mora_generada,
            "interes_extra_acumulado": interes_extra_generado,
            "intereses_ahorrados": intereses_ahorrados,
            "capital_adelantado": capital_adelantado,
            "cuotas_con_atraso": len(numeros_con_atraso),
            "cuotas_totales": len(cuotas),
            "numeros_con_atraso": numeros_con_atraso,
            "costos_totales": costos_totales,
            "ahorros_totales": ahorros_totales,
            "sobrecosto_total": balance,
            "hubo_decisiones": (
                costos_totales > 0
                or ahorros_totales > 0
                or len(numeros_con_atraso) > 0
            ),
        }

    def historial_decisiones(self, prestamo_id: int) -> list[dict]:
        """Devuelve los hitos que explican costos extra o intereses ahorrados."""
        pagos = self._pagos.por_prestamo(prestamo_id)
        eventos: list[dict] = []

        for pago in pagos:
            if pago.estado != "VALIDA":
                continue

            tipo = pago.tipo_pago or "CUOTA"

            if tipo == "PARCIAL" and pago.interes_extra_generado > 0:
                eventos.append({
                    "fecha": pago.fecha_real,
                    "tipo": "PAGO_PARCIAL",
                    "icono": "↩",
                    "titulo": "Pago parcial",
                    "descripcion": "Pagaste menos del total del mes",
                    "impacto": (
                        f"Ese monto generó "
                        f"{self._fmt(pago.interes_extra_generado)} "
                        "de interés extra al mes siguiente"
                    ),
                    "monto_impacto": pago.interes_extra_generado,
                })

            elif tipo in ("ADELANTO_RAI", "ADELANTO_RNI") and pago.intereses_ahorrados > 0:
                opcion = "RAI" if tipo == "ADELANTO_RAI" else "RNI"
                eventos.append({
                    "fecha": pago.fecha_real,
                    "tipo": tipo,
                    "icono": "💰",
                    "titulo": f"Adelanto {opcion}",
                    "descripcion": (
                        f"Adelantaste {self._fmt(pago.monto_a_capital)} a capital"
                    ),
                    "impacto": (
                        f"Ahorraste {self._fmt(pago.intereses_ahorrados)} "
                        "en intereses"
                    ),
                    "monto_impacto": -pago.intereses_ahorrados,
                })

        eventos.sort(key=lambda evento: evento["fecha"] or date.min)
        return eventos

    @staticmethod
    def _resumen_vacio() -> dict:
        """Mantiene el mismo formato cuando el préstamo no tiene versión activa."""
        cero = Decimal("0.00")
        return {
            "mora_pendiente": cero,
            "interes_extra_acumulado": cero,
            "intereses_ahorrados": cero,
            "capital_adelantado": cero,
            "cuotas_con_atraso": 0,
            "cuotas_totales": 0,
            "numeros_con_atraso": [],
            "costos_totales": cero,
            "ahorros_totales": cero,
            "sobrecosto_total": cero,
            "hubo_decisiones": False,
        }

    @staticmethod
    def _fmt(valor: Decimal) -> str:
        """Presenta importes en el formato usado por el resto de la UI argentina."""
        entero, decimales = f"{valor:.2f}".split(".")
        entero_con_puntos = f"{int(entero):,}".replace(",", ".")
        return f"$ {entero_con_puntos},{decimales}"


__all__ = ["ConsultaImpactoPagos"]
