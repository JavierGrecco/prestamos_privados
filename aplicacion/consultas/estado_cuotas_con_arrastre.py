"""Estado de cuotas de solo lectura para presentar el arrastre de deuda.

Esta consulta mantiene el desglose que ya muestra la aplicación: importes
contractuales, saldos pendientes que vienen de cuotas anteriores y los
importes adicionales que corresponden a la próxima cuota. No registra pagos
ni modifica el cronograma.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from dominio import ModalidadTasa, calcular_mora, tasa_mensual
from aplicacion.puertos.consulta_prestamo_pago import (
    RepositorioLecturaPrestamoPago,
    RepositorioPoliticaPagoLectura,
)


class ConsultaEstadoCuotasConArrastre:
    """Arma la vista de cuotas usando contratos de lectura, sin SQLite."""

    def __init__(
        self,
        prestamos: RepositorioLecturaPrestamoPago,
        politicas_pago: RepositorioPoliticaPagoLectura,
    ) -> None:
        self._prestamos = prestamos
        self._politicas_pago = politicas_pago

    def obtener(
        self,
        prestamo_id: int,
        fecha_calculo: date,
    ) -> list[dict[str, Any]]:
        """Devuelve las cuotas y el desglose calculado para la próxima.

        Se conserva la forma histórica de los datos que consume la interfaz.
        Los cálculos siguen las políticas registradas para el préstamo y la
        fecha indicada; esta consulta no escribe cambios en la base de datos.
        """
        version_id = self._prestamos.version_activa(prestamo_id)
        if version_id is None:
            return []

        info_tasa = self._prestamos.info_tasa_activa(prestamo_id)
        if info_tasa is None:
            return []

        politica = self._politicas_pago.obtener_vigente(
            prestamo_id,
            fecha_calculo,
        )
        i_mensual = tasa_mensual(
            info_tasa["tasa_anual"],
            ModalidadTasa(info_tasa["modalidad"]),
        )
        cuotas = self._prestamos.cuotas(version_id)

        proxima_idx = None
        for i, cuota in enumerate(cuotas):
            if cuota.estado == "PENDIENTE":
                proxima_idx = i
                break

        arrastre_capital = Decimal("0.00")
        arrastre_interes = Decimal("0.00")
        arrastre_mora = Decimal("0.00")
        resultado: list[dict[str, Any]] = []

        for i, cuota in enumerate(cuotas):
            item = {
                "numero": cuota.numero,
                "vencimiento": cuota.fecha_vencimiento,
                "estado": cuota.estado,
                "cuota_teorica": cuota.cuota,
                "interes_teorico": cuota.interes,
                "capital_teorico": cuota.capital,
                "saldo_teorico": cuota.saldo,
                "es_proxima": False,
                "monto_real": cuota.cuota,
                "desglose": None,
                "tuvo_pago_parcial": cuota.tuvo_pago_parcial,
                "fue_recalculada": cuota.fue_recalculada,
            }

            if i == proxima_idx:
                interes_extra = (
                    (arrastre_capital * i_mensual).quantize(Decimal("0.01"))
                    if politica.interes_compensatorio_post_vencimiento
                    else Decimal("0.00")
                )

                mora_nueva = Decimal("0.00")
                if (
                    politica.mora_habilitada
                    and cuota.fecha_vencimiento
                    and cuota.fecha_vencimiento < fecha_calculo
                ):
                    base_mora = (
                        cuota.cuota
                        if politica.mora_base.value == "CUOTA_CONTRACTUAL"
                        else cuota.capital
                    )
                    mora_nueva = calcular_mora(
                        monto_vencido=base_mora,
                        tasa_mora_anual=politica.mora_tasa_anual,
                        fecha_vencimiento=cuota.fecha_vencimiento,
                        fecha_calculo=fecha_calculo,
                    )

                tiene_arrastre = (
                    arrastre_capital > 0
                    or arrastre_interes > 0
                    or arrastre_mora > 0
                    or interes_extra > 0
                    or mora_nueva > 0
                )

                item["es_proxima"] = True
                item["monto_real"] = (
                    cuota.cuota
                    + arrastre_capital
                    + arrastre_interes
                    + arrastre_mora
                    + interes_extra
                    + mora_nueva
                )

                if tiene_arrastre:
                    item["desglose"] = {
                        "cuota_teorica": cuota.cuota,
                        "arrastre_capital": arrastre_capital,
                        "arrastre_interes": arrastre_interes,
                        "arrastre_mora": arrastre_mora,
                        "interes_extra": interes_extra,
                        "mora_nueva": mora_nueva,
                    }

            # El arrastre que verá la próxima cuota se acumula con los importes
            # pendientes de cada cuota anterior en el mismo orden del historial.
            arrastre_capital += cuota.capital_pendiente
            arrastre_interes += cuota.interes_pendiente
            arrastre_mora += cuota.mora_pendiente
            resultado.append(item)

        return resultado


__all__ = ["ConsultaEstadoCuotasConArrastre"]
