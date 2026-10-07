"""Proyección económica común para comparar Legacy y V3.

Este módulo pertenece al soporte de equivalencia de tests. No contiene reglas
financieras ni forma parte del runtime de la aplicación.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


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


@dataclass(frozen=True)
class ComparacionPago:
    diferencias: tuple[DiferenciaPago, ...]

    @property
    def ok(self) -> bool:
        return not self.diferencias


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
    if correlaciones:
        corr = str(correlaciones[0]["correlacion_id"])
        ledger_rows = db.consultar(
            """SELECT entidad, entidad_id, tipo_movimiento, debe, haber
               FROM ledger
               WHERE correlacion_id = ?
               ORDER BY id""",
            (corr,),
        )
    else:
        ledger_rows = ()


    ledger = tuple(
        (
            str(row["entidad"]),
            int(row["entidad_id"]),
            str(row["tipo_movimiento"]),
            _dec(row["debe"]),
            _dec(row["haber"]),
        )
        for row in ledger_rows
    )

    distribuciones: dict[int, Decimal] = {}
    for row in ledger:
        entidad, entidad_id, tipo, debe, haber = row
        if entidad == "INVERSOR" and tipo == "COBRO_PAGO":
            distribuciones[entidad_id] = (
                distribuciones.get(entidad_id, Decimal("0")) + debe
            )

    auditorias = db.consultar(
        """SELECT operacion
           FROM auditoria
           WHERE entidad = 'PAGO' AND entidad_id = ?
           ORDER BY id""",
        (pago_id,),
    )

    return ProyeccionPago(
        monto=_dec(pago["monto_moneda_contractual"]),
        tipo_pago=str(pago["tipo_pago"] or "CUOTA"),
        interes_extra_generado=_dec(pago["interes_extra_generado"]),
        intereses_ahorrados=_dec(pago["intereses_ahorrados"]),
        opcion_adelanto=pago["opcion_adelanto"],
        imputaciones=imputaciones,
        cuotas=cuotas,
        distribuciones=tuple(sorted(distribuciones.items())),
        ledger=ledger,
        auditoria_principal_presente=any(
            str(row["operacion"]).startswith("PAGO_REGISTRADO")
            for row in auditorias
        ),
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
