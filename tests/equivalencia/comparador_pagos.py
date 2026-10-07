"""Proyección económica común para comparar Legacy y V3.

Este módulo pertenece al soporte de equivalencia de tests. No contiene reglas
financieras ni forma parte del runtime de la aplicación.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Any

CENT = Decimal("0.01")


def _dec(value: Any) -> Decimal:
    return Decimal(str(value if value is not None else "0"))


@dataclass(frozen=True)
class DiferenciaPago:
    ruta: str
    esperado: Any
    obtenido: Any


@dataclass(frozen=True)
class ProyeccionPago:
    monto: Decimal
    tipo_pago: str
    interes_extra_generado: Decimal
    intereses_ahorrados: Decimal
    opcion_adelanto: str | None
    imputaciones: tuple[tuple[int | None, str, Decimal], ...]
    cuotas: tuple[
        tuple[int, str, Decimal, Decimal, Decimal, Decimal], ...
    ]
    distribuciones: tuple[tuple[int, Decimal], ...]
    ledger: tuple[tuple[str, int, str, Decimal, Decimal], ...]
    auditoria_principal_presente: bool
    observaciones: tuple[str, ...]


@dataclass(frozen=True)
class ComparacionPago:
    diferencias: tuple[DiferenciaPago, ...]

    @property
    def ok(self) -> bool:
        return not self.diferencias


def _normalizar_distribuciones(
    distribuciones_raw: dict[int, Decimal],
    monto_total: Decimal,
) -> tuple[tuple[int, Decimal], ...]:
    """Lleva distribuciones históricas a centavos sin perder el total."""
    monto_total = monto_total.quantize(CENT, rounding=ROUND_HALF_UP)
    if not distribuciones_raw:
        return tuple()

    calculos = []
    asignado = Decimal("0")
    for inversor_id, bruto in distribuciones_raw.items():
        base = bruto.quantize(CENT, rounding=ROUND_DOWN)
        resto = bruto - base
        calculos.append((inversor_id, base, resto))
        asignado += base

    restante = monto_total - asignado
    if restante < Decimal("0") or restante % CENT != Decimal("0"):
        raise AssertionError(
            f"Distribución histórica incompatible con centavos: "
            f"total={monto_total}, asignado={asignado}"
        )

    centavos = int(restante / CENT)
    orden = sorted(calculos, key=lambda x: (-x[2], x[0]))
    adicionales = {inversor_id: 0 for inversor_id, _, _ in calculos}
    for i in range(centavos):
        adicionales[orden[i % len(orden)][0]] += 1

    return tuple(
        sorted(
            (
                inversor_id,
                (base + CENT * adicionales[inversor_id]).quantize(
                    CENT, rounding=ROUND_HALF_UP
                ),
            )
            for inversor_id, base, _ in calculos
        )
    )


def proyectar_pago(db: Any, pago_id: int) -> ProyeccionPago:
    pago = db.consultar_uno(
        """SELECT id, prestamo_id, monto_moneda_contractual, tipo_pago,
                  interes_extra_generado, intereses_ahorrados, opcion_adelanto
           FROM pagos WHERE id = ?""",
        (pago_id,),
    )
    if pago is None:
        raise AssertionError(f"No existe el pago {pago_id}")

    prestamo_id = int(pago["prestamo_id"])
    monto = _dec(pago["monto_moneda_contractual"])

    cuotas_rows = db.consultar(
        """SELECT c.id, c.numero, c.estado,
                  c.interes_pendiente, c.capital_pendiente,
                  c.mora_pendiente, c.monto_pendiente
           FROM cuotas c
           JOIN versiones_tasa v ON v.id = c.version_id
           WHERE v.prestamo_id = ?
           ORDER BY c.numero, c.id""",
        (prestamo_id,),
    )
    cuota_numero = {int(f["id"]): int(f["numero"]) for f in cuotas_rows}

    imputaciones_rows = db.consultar(
        """SELECT cuota_id, concepto, monto
           FROM imputaciones
           WHERE pago_id = ?
           ORDER BY id""",
        (pago_id,),
    )
    imputaciones = tuple(
        (
            None if row["cuota_id"] is None else cuota_numero[int(row["cuota_id"])],
            str(row["concepto"]),
            _dec(row["monto"]),
        )
        for row in imputaciones_rows
    )

    cuotas = tuple(
        (
            int(row["numero"]),
            str(row["estado"]),
            _dec(row["mora_pendiente"]),
            _dec(row["interes_pendiente"]),
            _dec(row["capital_pendiente"]),
            _dec(row["monto_pendiente"]),
        )
        for row in cuotas_rows
    )

    correlaciones = db.consultar(
        """SELECT correlacion_id
           FROM ledger
           WHERE entidad = 'PAGO' AND entidad_id = ?
           ORDER BY id
           LIMIT 1""",
        (pago_id,),
    )
    ledger_rows = ()
    if correlaciones:
        corr = str(correlaciones[0]["correlacion_id"])
        ledger_rows = db.consultar(
            """SELECT entidad, entidad_id, tipo_movimiento, debe, haber
               FROM ledger
               WHERE correlacion_id = ?
               ORDER BY id""",
            (corr,),
        )

    ledger = tuple(
        (
            str(row["entidad"]),
            int(row["entidad_id"]),
            str(row["tipo_movimiento"]),
            _dec(row["debe"]),
            _dec(row["haber"]),
        )
        for row in ledger_rows
        if str(row["entidad"]) != "INVERSOR"
        and str(row["tipo_movimiento"]) != "DISTRIBUCION_INVERSOR"
    )

    distribuciones_raw: dict[int, Decimal] = {}
    for row in ledger_rows:
        if (
            str(row["entidad"]) == "INVERSOR"
            and str(row["tipo_movimiento"]) == "COBRO_PAGO"
        ):
            inversor_id = int(row["entidad_id"])
            distribuciones_raw[inversor_id] = (
                distribuciones_raw.get(inversor_id, Decimal("0"))
                + _dec(row["debe"])
            )

    distribuciones = _normalizar_distribuciones(
        distribuciones_raw,
        monto,
    )

    observaciones = []
    for inversor_id, bruto in sorted(distribuciones_raw.items()):
        canonico = dict(distribuciones).get(inversor_id, Decimal("0"))
        if bruto != canonico:
            observaciones.append(
                "distribucion_con_precision_subcentavo_en_fuente"
            )
            break

    auditorias = db.consultar(
        """SELECT operacion
           FROM auditoria
           WHERE entidad = 'PAGO' AND entidad_id = ?
           ORDER BY id""",
        (pago_id,),
    )

    return ProyeccionPago(
        monto=monto,
        tipo_pago=str(pago["tipo_pago"] or "CUOTA"),
        interes_extra_generado=_dec(pago["interes_extra_generado"]),
        intereses_ahorrados=_dec(pago["intereses_ahorrados"]),
        opcion_adelanto=pago["opcion_adelanto"],
        imputaciones=imputaciones,
        cuotas=cuotas,
        distribuciones=distribuciones,
        ledger=ledger,
        auditoria_principal_presente=any(
            str(row["operacion"]).startswith("PAGO_REGISTRADO")
            for row in auditorias
        ),
        observaciones=tuple(observaciones),
    )


def comparar_pagos(
    esperado: ProyeccionPago,
    obtenido: ProyeccionPago,
) -> ComparacionPago:
    diferencias: list[DiferenciaPago] = []
    campos = (
        ("monto", esperado.monto, obtenido.monto),
        ("tipo_pago", esperado.tipo_pago, obtenido.tipo_pago),
        (
            "interes_extra_generado",
            esperado.interes_extra_generado,
            obtenido.interes_extra_generado,
        ),
        (
            "intereses_ahorrados",
            esperado.intereses_ahorrados,
            obtenido.intereses_ahorrados,
        ),
        ("opcion_adelanto", esperado.opcion_adelanto, obtenido.opcion_adelanto),
        ("imputaciones", esperado.imputaciones, obtenido.imputaciones),
        ("cuotas", esperado.cuotas, obtenido.cuotas),
        ("distribuciones", esperado.distribuciones, obtenido.distribuciones),
        ("ledger", esperado.ledger, obtenido.ledger),
        (
            "auditoria_principal_presente",
            esperado.auditoria_principal_presente,
            obtenido.auditoria_principal_presente,
        ),
    )
    for ruta, lhs, rhs in campos:
        if lhs != rhs:
            diferencias.append(DiferenciaPago(ruta, lhs, rhs))
    return ComparacionPago(tuple(diferencias))
