"""Simulación de un adelanto sin modificar el préstamo.

La consulta prepara dos alternativas para una decisión del usuario:
reducir el importe de las cuotas (RAI) o reducir la cantidad de cuotas (RNI).
La deuda y la política vigente se obtienen mediante la función inyectada, para
conservar la misma resolución histórica de tasas y políticas que usa pagos.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Protocol

from dominio import ModalidadTasa, SistemaAmortizacion
from dominio.recalculo import recalcular_rai, recalcular_rni, calcular_impacto
from aplicacion.puertos.consulta_prestamo_pago import (
    RepositorioLecturaPrestamoPago,
)


class CalculadorDeudaParaSimulacion(Protocol):
    """Capacidad para obtener la deuda por el camino público ya existente."""

    def __call__(
        self,
        prestamo_id: int,
        fecha_calculo: date,
    ) -> dict[str, Any] | None: ...


class ConsultaSimulacionAdelantoLegacy:
    """Calcula alternativas RAI/RNI y solo devuelve una proyección."""

    def __init__(
        self,
        prestamos: RepositorioLecturaPrestamoPago,
        calcular_deuda: CalculadorDeudaParaSimulacion,
    ) -> None:
        self._prestamos = prestamos
        self._calcular_deuda = calcular_deuda

    def simular(
        self,
        prestamo_id: int,
        monto_adelanto: Decimal,
        fecha_calculo: date,
    ) -> dict[str, Any] | None:
        """Devuelve la proyección histórica sin persistir ni cambiar cuotas."""
        deuda = self._calcular_deuda(prestamo_id, fecha_calculo)
        if deuda is None:
            return None

        version_id = self._prestamos.version_activa(prestamo_id)
        info_tasa = self._prestamos.info_tasa_activa(prestamo_id)
        if info_tasa is None:
            return None

        cuota_obj = deuda["cuota_objetivo"]
        cuotas_actuales = self._prestamos.cuotas(version_id)

        cuotas_futuras = []
        encontrado = False
        for cuota in cuotas_actuales:
            if cuota.id == cuota_obj.id:
                encontrado = True
                continue
            if encontrado and cuota.estado == "PENDIENTE":
                cuotas_futuras.append(cuota)

        if not cuotas_futuras:
            return None

        capital_al_final_objetivo = cuota_obj.saldo
        capital_nuevo = capital_al_final_objetivo - monto_adelanto
        if capital_nuevo < 0:
            capital_nuevo = Decimal("0.00")

        meses_restantes = len(cuotas_futuras)
        fecha_ultimo_venc = cuotas_futuras[-1].fecha_vencimiento
        cuota_referencia = cuota_obj.cuota

        # Mantener el tratamiento histórico: si RAI no puede calcularse,
        # devolvemos esa alternativa sin resultado pero seguimos con RNI.
        try:
            tabla_rai = recalcular_rai(
                capital_pendiente=capital_nuevo,
                tasa_anual=info_tasa["tasa_anual"],
                modalidad=ModalidadTasa(info_tasa["modalidad"]),
                meses_restantes=meses_restantes,
                fecha_ultimo_vencimiento=fecha_ultimo_venc,
                sistema=SistemaAmortizacion("frances"),
            )
            imp_rai = calcular_impacto(
                [
                    {"interes": cuota.interes, "cuota": cuota.cuota}
                    for cuota in cuotas_futuras
                ],
                tabla_rai,
            )
        except Exception:
            tabla_rai = None
            imp_rai = None

        tabla_rni, n_rni = recalcular_rni(
            capital_pendiente=capital_nuevo,
            tasa_anual=info_tasa["tasa_anual"],
            modalidad=ModalidadTasa(info_tasa["modalidad"]),
            cuota_objetivo=cuota_referencia,
            fecha_ultimo_vencimiento=fecha_ultimo_venc,
            sistema=SistemaAmortizacion("frances"),
        )

        if tabla_rni is not None:
            imp_rni = calcular_impacto(
                [
                    {"interes": cuota.interes, "cuota": cuota.cuota}
                    for cuota in cuotas_futuras
                ],
                tabla_rni,
            )
        else:
            imp_rni = None

        return {
            "capital_pendiente_actual": capital_al_final_objetivo,
            "capital_despues_adelanto": capital_nuevo,
            "monto_adelanto": monto_adelanto,
            "cuotas_restantes_antes": meses_restantes,
            "fecha_ultimo_vencimiento": fecha_ultimo_venc,
            "rai": {"tabla": tabla_rai, "impacto": imp_rai},
            "rni": {
                "tabla": tabla_rni,
                "cuotas_nuevas": n_rni,
                "impacto": imp_rni,
            },
        }


__all__ = ["ConsultaSimulacionAdelantoLegacy"]
