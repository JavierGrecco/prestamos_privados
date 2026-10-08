"""Servicio de aplicación para simulaciones de nuevos préstamos.

La UI puede pedir simulaciones sin conocer el motor de amortización ni repetir
sus fórmulas. Todo cálculo financiero sigue viviendo en dominio/.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from dominio import (
    ConvencionDias,
    ModalidadTasa,
    SistemaAmortizacion,
    generar_tabla,
)
from dominio.interes import interes_periodo


@dataclass(frozen=True)
class ResultadoComparacionTasas:
    """Cuotas iniciales calculadas con ambas modalidades."""

    tna: Decimal | None
    tea: Decimal | None


class ServicioSimulacionPrestamo:
    """Consulta de simulación para la UI y otros consumidores."""

    def generar_tabla(
        self,
        *,
        capital: Decimal,
        tasa_anual: Decimal,
        plazo_meses: int,
        modalidad_tasa: ModalidadTasa,
        sistema: SistemaAmortizacion,
        fecha_inicio: date,
    ) -> list[dict]:
        return generar_tabla(
            capital=capital,
            tasa_anual=tasa_anual,
            modalidad=modalidad_tasa,
            meses=plazo_meses,
            fecha_inicio=fecha_inicio,
            sistema=sistema,
        )

    def cuota_inicial(
        self,
        *,
        capital: Decimal,
        tasa_anual: Decimal,
        plazo_meses: int,
        modalidad_tasa: ModalidadTasa,
        sistema: SistemaAmortizacion,
        fecha_inicio: date,
    ) -> Decimal | None:
        tabla = self.generar_tabla(
            capital=capital,
            tasa_anual=tasa_anual,
            plazo_meses=plazo_meses,
            modalidad_tasa=modalidad_tasa,
            sistema=sistema,
            fecha_inicio=fecha_inicio,
        )
        return tabla[0]["cuota"] if tabla else None

    def comparar_tasas(
        self,
        *,
        capital: Decimal,
        tasa_anual: Decimal,
        plazo_meses: int,
        sistema: SistemaAmortizacion,
        fecha_inicio: date,
    ) -> ResultadoComparacionTasas:
        def calcular(modalidad: ModalidadTasa) -> Decimal | None:
            return self.cuota_inicial(
                capital=capital,
                tasa_anual=tasa_anual,
                plazo_meses=plazo_meses,
                modalidad_tasa=modalidad,
                sistema=sistema,
                fecha_inicio=fecha_inicio,
            )

        return ResultadoComparacionTasas(
            tna=calcular(ModalidadTasa.TNA),
            tea=calcular(ModalidadTasa.TEA),
        )

    def interes_primer_periodo(
        self,
        *,
        capital: Decimal,
        tasa_anual: Decimal,
        modalidad_tasa: ModalidadTasa,
        convencion_dias: ConvencionDias,
        fecha_inicio: date,
    ) -> Decimal:
        fecha_fin = fecha_inicio + relativedelta(months=1)
        return interes_periodo(
            saldo=capital,
            tasa_anual=tasa_anual,
            modalidad=modalidad_tasa,
            convencion=convencion_dias,
            fecha_ini=fecha_inicio,
            fecha_fin=fecha_fin,
        )

    def comparar_convenciones_primer_periodo(
        self,
        *,
        capital: Decimal,
        tasa_anual: Decimal,
        modalidad_tasa: ModalidadTasa,
        fecha_inicio: date,
    ) -> dict[ConvencionDias, Decimal]:
        return {
            convencion: self.interes_primer_periodo(
                capital=capital,
                tasa_anual=tasa_anual,
                modalidad_tasa=modalidad_tasa,
                convencion_dias=convencion,
                fecha_inicio=fecha_inicio,
            )
            for convencion in (
                ConvencionDias.MENSUAL,
                ConvencionDias.ACTUAL_365,
                ConvencionDias.ACTUAL_360,
                ConvencionDias.TREINTA_360,
            )
        }
