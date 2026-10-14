"""G7: read model auditable de un pago V3.

Solo lectura. No recalcula, no modifica estado y no ejecuta operaciones de
negocio. Su objetivo es exponer la cadena PAGO -> CUOTA -> CONCEPTO -> MONTO,
los movimientos contables y la auditoría de una operación.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json

from dominio.excepciones import ErrorInvariante, ErrorValidacion
from dominio.tipos import money

from aplicacion.puertos.pago_v3_auditable import (
    AuditoriaPagoV3Read,
    ImputacionPagoV3Read,
    MovimientoLedgerPagoV3Read,
    PagoV3Read,
    ReconciliacionPagoV3Read,
)


ZERO = Decimal("0.00")


def obtener_pago_v3(db, pago_id: int) -> PagoV3Read:
    """Obtiene una representación auditable y consistente de un pago V3."""
    if pago_id <= 0:
        raise ErrorValidacion("El pago_id debe ser positivo")

    fila = db.consultar_uno(
        """
        SELECT id, prestamo_id, fecha_real, fecha_valor,
               monto_moneda_contractual, moneda_pago, tipo_pago,
               monto_a_capital, intereses_ahorrados,
               cuotas_restantes_antes, cuotas_restantes_despues,
               opcion_adelanto, motor_version, plan_hash, plan_json
        FROM pagos
        WHERE id = ?
        """,
        (pago_id,),
    )
    if fila is None:
        raise ErrorValidacion(f"El pago {pago_id} no existe")

    imputaciones = tuple(
        ImputacionPagoV3Read(
            id=int(f["id"]),
            cuota_id=None if f["cuota_id"] is None else int(f["cuota_id"]),
            concepto=str(f["concepto"]),
            monto=_decimal(f["monto"]),
            origen=str(f["origen"]),
            referencias_devengamiento=_referencias(f["referencias_devengamiento"]),
        )
        for f in db.consultar(
            """
            SELECT id, cuota_id, concepto, monto, origen, referencias_devengamiento
            FROM imputaciones
            WHERE pago_id = ?
            ORDER BY id
            """,
            (pago_id,),
        )
    )

    ledger = tuple(
        MovimientoLedgerPagoV3Read(
            id=int(f["id"]),
            entidad=str(f["entidad"]),
            entidad_id=int(f["entidad_id"]),
            tipo_movimiento=str(f["tipo_movimiento"]),
            debe=_decimal(f["debe"]),
            haber=_decimal(f["haber"]),
            fecha=str(f["fecha"]),
            correlacion_id=str(f["correlacion_id"]),
        )
        for f in db.consultar(
            """
            SELECT id, entidad, entidad_id, tipo_movimiento, debe, haber, fecha, correlacion_id
            FROM ledger
            WHERE (entidad='PAGO' AND entidad_id=?)
               OR json_extract(metadata, '$.pago_id') = ?
            ORDER BY id
            """,
            (pago_id, pago_id),
        )
    )

    auditoria = tuple(
        AuditoriaPagoV3Read(
            id=int(f["id"]),
            fecha=str(f["fecha"]),
            usuario=str(f["usuario"]),
            operacion=str(f["operacion"]),
            entidad=str(f["entidad"]),
            entidad_id=None if f["entidad_id"] is None else int(f["entidad_id"]),
            motivo=None if f["motivo"] is None else str(f["motivo"]),
            correlacion_id=str(f["correlacion_id"]),
        )
        for f in db.consultar(
            """
            SELECT id, fecha, usuario, operacion, entidad, entidad_id, motivo, correlacion_id
            FROM auditoria
            WHERE entidad='PAGO' AND entidad_id=?
            ORDER BY id
            """,
            (pago_id,),
        )
    )

    monto = money(_decimal(fila["monto_moneda_contractual"]))
    suma_imputaciones = money(sum((x.monto for x in imputaciones), ZERO))
    suma_ledger_pago_debe = money(
        sum(
            (x.debe for x in ledger if x.entidad == "PAGO" and x.tipo_movimiento == "PAGO"),
            ZERO,
        )
    )
    suma_ledger_prestamo_haber = money(
        sum(
            (x.haber for x in ledger if x.entidad == "PRESTAMO" and x.tipo_movimiento == "PAGO_RECIBIDO"),
            ZERO,
        )
    )
    suma_distribucion = money(
        sum(
            (x.haber for x in ledger if x.entidad == "PRESTAMO" and x.tipo_movimiento == "DISTRIBUCION_INVERSOR"),
            ZERO,
        )
    )
    hay_distribucion = any(
        x.entidad == "PRESTAMO" and x.tipo_movimiento == "DISTRIBUCION_INVERSOR"
        for x in ledger
    )

    reconciliacion = ReconciliacionPagoV3Read(
        monto_pago=monto,
        suma_imputaciones=suma_imputaciones,
        suma_ledger_pago_debe=suma_ledger_pago_debe,
        suma_ledger_prestamo_haber=suma_ledger_prestamo_haber,
        suma_distribucion_inversores=suma_distribucion,
        hay_distribucion_inversores=hay_distribucion,
    )
    if not reconciliacion.integra:
        raise ErrorInvariante(
            "La lectura auditable detectó una inconsistencia financiera en el pago "
            f"{pago_id}"
        )

    plan = None
    plan_json = fila["plan_json"]
    plan_hash = None if fila["plan_hash"] is None else str(fila["plan_hash"])
    if plan_json:
        try:
            plan = json.loads(plan_json)
        except json.JSONDecodeError as exc:
            raise ErrorInvariante(f"El plan_json del pago {pago_id} no es JSON válido") from exc
        if plan_hash:
            hash_obtenido = hashlib.sha256(str(plan_json).encode("utf-8")).hexdigest()
            if hash_obtenido != plan_hash:
                raise ErrorInvariante(f"El plan_hash del pago {pago_id} no concilia con plan_json")

    correlaciones = {x.correlacion_id for x in ledger}
    if len(correlaciones) > 1:
        raise ErrorInvariante(f"El pago {pago_id} tiene movimientos de ledger con correlaciones distintas")
    if ledger:
        corr_pago = correlaciones.pop()
        if not all(a.correlacion_id == corr_pago for a in auditoria):
            raise ErrorInvariante(f"La auditoría del pago {pago_id} no comparte la correlación del ledger")

    return PagoV3Read(
        pago_id=int(fila["id"]),
        prestamo_id=int(fila["prestamo_id"]),
        fecha_real=str(fila["fecha_real"]),
        fecha_valor=str(fila["fecha_valor"]),
        monto=monto,
        moneda=str(fila["moneda_pago"]),
        tipo_pago=str(fila["tipo_pago"]),
        monto_a_capital=_decimal(fila["monto_a_capital"]),
        intereses_ahorrados=_decimal(fila["intereses_ahorrados"]),
        cuotas_restantes_antes=int(fila["cuotas_restantes_antes"]),
        cuotas_restantes_despues=int(fila["cuotas_restantes_despues"]),
        opcion_adelanto=None if fila["opcion_adelanto"] is None else str(fila["opcion_adelanto"]),
        motor_version=str(fila["motor_version"]),
        plan_hash=None if fila["plan_hash"] is None else str(fila["plan_hash"]),
        plan=plan,
        imputaciones=imputaciones,
        ledger=ledger,
        auditoria=auditoria,
        reconciliacion=reconciliacion,
    )


def _decimal(valor) -> Decimal:
    if valor is None or valor == "":
        return ZERO
    return Decimal(str(valor))


def _referencias(valor) -> tuple[str, ...]:
    if valor is None or valor == "":
        return ()
    try:
        data = json.loads(str(valor))
    except json.JSONDecodeError as exc:
        raise ErrorInvariante("referencias_devengamiento contiene JSON inválido") from exc
    if not isinstance(data, list):
        raise ErrorInvariante("referencias_devengamiento debe ser una lista JSON")
    return tuple(str(x) for x in data if x)

class ConsultaPagoV3SQLite:
    """Implementación SQLite del puerto de lectura auditable de pagos V3."""

    def __init__(self, db) -> None:
        self._db = db

    def obtener_pago_v3(self, pago_id: int) -> PagoV3Read:
        """Reutiliza el lector auditable existente como única fuente de datos."""
        return obtener_pago_v3(self._db, pago_id)


__all__ = [
    "ImputacionPagoV3Read",
    "MovimientoLedgerPagoV3Read",
    "AuditoriaPagoV3Read",
    "ReconciliacionPagoV3Read",
    "PagoV3Read",
    "obtener_pago_v3",
    "ConsultaPagoV3SQLite",
]

