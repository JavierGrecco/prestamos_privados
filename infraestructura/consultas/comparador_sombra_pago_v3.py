"""Comparador de economía Legacy vs PlanPago V3 para SOMBRA.

Lee únicamente el resultado Legacy ya persistido y lo compara con el plan
V3 calculado sobre el snapshot previo. No modifica datos.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from infraestructura.repositorios.pagos import PagoRepo


def _dec(value: Any) -> Decimal:
    return Decimal(str(value if value is not None else "0"))


@dataclass(frozen=True)
class DiferenciaSombra:
    campo: str
    legacy: Any
    v3: Any

    def resumen(self) -> str:
        return f"{self.campo}: Legacy={self.legacy!r}, V3={self.v3!r}"


class ComparadorSombraPagoSQLite:
    """Compara el resultado Legacy contra un PlanPago V3 sin persistir."""

    def __init__(self, db) -> None:
        self._db = db
        self._pagos = PagoRepo(db)

    def comparar(
        self,
        resultado_legacy: Any,
        plan_v3: Any,
    ) -> str | None:
        if not isinstance(resultado_legacy, int):
            return DiferenciaSombra(
                "pago_id_legacy", type(resultado_legacy).__name__, "int esperado"
            ).resumen()

        pago = self._pagos.obtener(resultado_legacy)
        if pago is None:
            return DiferenciaSombra(
                "pago_legacy", "no existe", "debe existir"
            ).resumen()

        diferencias: list[DiferenciaSombra] = []

        self._agregar(
            diferencias,
            "monto",
            pago.monto_moneda_contractual,
            plan_v3.monto_pago_recibido,
        )
        self._agregar(
            diferencias,
            "tipo_pago",
            pago.tipo_pago or "CUOTA",
            plan_v3.tipo.value,
        )

        imputaciones_legacy = self._imputaciones_por_numero(pago.id)
        numeros_cuota = {
            obligacion.cuota_id: obligacion.numero_cuota
            for obligacion in plan_v3.obligaciones_afectadas
        }
        imputaciones_v3 = tuple(
            (
                numeros_cuota.get(aplicacion.cuota_id),
                aplicacion.concepto.value,
                aplicacion.monto,
            )
            for aplicacion in plan_v3.aplicaciones
        )

        self._agregar(
            diferencias,
            "imputaciones",
            imputaciones_legacy,
            imputaciones_v3,
        )

        for obligacion in plan_v3.obligaciones_afectadas:
            actual = self._db.consultar_uno(
                """SELECT estado, mora_pendiente, interes_pendiente,
                          capital_pendiente, monto_pendiente
                   FROM cuotas
                   WHERE id = ?""",
                (obligacion.cuota_id,),
            )
            if actual is None:
                diferencias.append(
                    DiferenciaSombra(
                        f"cuota[{obligacion.numero_cuota}]",
                        "no existe",
                        obligacion.saldo_posterior,
                    )
                )
                continue

            saldo_legacy = (
                _dec(actual["mora_pendiente"]),
                _dec(actual["interes_pendiente"]),
                _dec(actual["capital_pendiente"]),
            )
            saldo_v3 = (
                obligacion.saldo_posterior.mora,
                obligacion.saldo_posterior.interes,
                obligacion.saldo_posterior.capital,
            )
            self._agregar(
                diferencias,
                f"cuota[{obligacion.numero_cuota}].saldo_mora_interes_capital",
                saldo_legacy,
                saldo_v3,
            )
            self._agregar(
                diferencias,
                f"cuota[{obligacion.numero_cuota}].estado",
                str(actual["estado"]),
                obligacion.estado_posterior,
            )

        if not diferencias:
            return None

        return "; ".join(d.resumen() for d in diferencias)

    def _imputaciones_por_numero(
        self,
        pago_id: int,
    ) -> tuple[tuple[int | None, str, Decimal], ...]:
        filas = self._db.consultar(
            """SELECT i.cuota_id, i.concepto, i.monto, c.numero
               FROM imputaciones i
               LEFT JOIN cuotas c ON c.id = i.cuota_id
               WHERE i.pago_id = ?
               ORDER BY i.id""",
            (pago_id,),
        )
        return tuple(
            (
                None if row["numero"] is None else int(row["numero"]),
                str(row["concepto"]),
                _dec(row["monto"]),
            )
            for row in filas
        )

    @staticmethod
    def _agregar(
        diferencias: list[DiferenciaSombra],
        campo: str,
        legacy: Any,
        v3: Any,
    ) -> None:
        if legacy != v3:
            diferencias.append(DiferenciaSombra(campo, legacy, v3))
