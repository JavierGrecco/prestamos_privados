"""Adaptador SQLite para lecturas persistidas del detalle financiero."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from aplicacion.puertos.detalle_financiero_prestamo import (
    CuotaDetalleLectura,
    DevengamientoDetalleLectura,
    ImputacionCapitalDetalleLectura,
    PrestamoDetalleLectura,
    RecalculoDetalleLectura,
)
from dominio.tipos import ConceptoImputacion
from infraestructura.db import BaseDatos
from infraestructura.repositorios import PrestamoRepo


class DetalleFinancieroPrestamoSQLiteQuery:
    """Ejecuta exclusivamente las lecturas SQLite del detalle financiero."""

    def __init__(self, db: BaseDatos) -> None:
        self._db = db
        self._prestamos = PrestamoRepo(db)

    def obtener_prestamo(self, prestamo_id: int) -> PrestamoDetalleLectura | None:
        prestamo = self._prestamos.obtener(prestamo_id)
        if prestamo is None:
            return None
        if prestamo.id is None:
            return None
        return PrestamoDetalleLectura(
            prestamo_id=int(prestamo.id),
            numero=str(prestamo.numero),
            capital_original=prestamo.capital_original,
            fecha_inicio=prestamo.fecha_inicio,
        )

    def version_activa(self, prestamo_id: int) -> int | None:
        return self._prestamos.version_activa(prestamo_id)

    def cuotas(self, version_id: int) -> tuple[CuotaDetalleLectura, ...]:
        filas = self._db.consultar(
            """
            SELECT id, numero, fecha_vencimiento, estado,
                   capital_inicial, interes, capital, cuota, saldo,
                   monto_pendiente, interes_pendiente, capital_pendiente,
                   mora_pendiente, fue_mora, tuvo_pago_parcial,
                   fue_recalculada
            FROM cuotas
            WHERE version_id = ?
            ORDER BY numero, id
            """,
            (version_id,),
        )
        return tuple(
            CuotaDetalleLectura(
                id=int(f["id"]),
                numero=int(f["numero"]),
                vencimiento=date.fromisoformat(f["fecha_vencimiento"]),
                estado=str(f["estado"]),
                capital_inicial=Decimal(str(f["capital_inicial"])),
                interes=Decimal(str(f["interes"])),
                capital=Decimal(str(f["capital"])),
                cuota=Decimal(str(f["cuota"])),
                saldo=Decimal(str(f["saldo"])),
                monto_pendiente=Decimal(str(f["monto_pendiente"])),
                interes_pendiente=(
                    None
                    if f["interes_pendiente"] is None
                    else Decimal(str(f["interes_pendiente"]))
                ),
                capital_pendiente=(
                    None
                    if f["capital_pendiente"] is None
                    else Decimal(str(f["capital_pendiente"]))
                ),
                mora_pendiente=Decimal(str(f["mora_pendiente"])),
                fue_mora=bool(f["fue_mora"]),
                tuvo_pago_parcial=bool(f["tuvo_pago_parcial"]),
                fue_recalculada=bool(f["fue_recalculada"]),
            )
            for f in filas
        )

    def devengamientos(
        self, prestamo_id: int
    ) -> tuple[DevengamientoDetalleLectura, ...]:
        filas = self._db.consultar(
            """
            SELECT id, cuota_id, concepto, monto, fecha_desde, fecha_hasta,
                   origen, referencia, base, tasa_anual, dias, motor_version
            FROM devengamientos
            WHERE prestamo_id = ?
            ORDER BY fecha_hasta, id
            """,
            (prestamo_id,),
        )
        return tuple(
            DevengamientoDetalleLectura(
                id=int(f["id"]),
                cuota_id=int(f["cuota_id"]) if f["cuota_id"] is not None else None,
                concepto=str(f["concepto"]),
                monto=Decimal(str(f["monto"])),
                fecha_desde=date.fromisoformat(f["fecha_desde"]),
                fecha_hasta=date.fromisoformat(f["fecha_hasta"]),
                origen=str(f["origen"]),
                referencia=f["referencia"],
                base=Decimal(str(f["base"])),
                tasa_anual=Decimal(str(f["tasa_anual"])),
                dias=int(f["dias"]),
                motor_version=str(f["motor_version"]),
            )
            for f in filas
        )

    def recalculos(
        self, prestamo_id: int
    ) -> tuple[RecalculoDetalleLectura, ...]:
        filas = self._db.consultar(
            """
            SELECT id, pago_id, tipo, fecha, capital_antes, capital_despues,
                   cuotas_antes, cuotas_despues, intereses_antes,
                   intereses_despues, detalle_json
            FROM historial_recalculos
            WHERE prestamo_id = ?
            ORDER BY fecha, id
            """,
            (prestamo_id,),
        )
        return tuple(
            RecalculoDetalleLectura(
                id=int(f["id"]),
                pago_id=int(f["pago_id"]),
                tipo=str(f["tipo"]),
                fecha=date.fromisoformat(str(f["fecha"])[:10]),
                capital_antes=Decimal(str(f["capital_antes"])),
                capital_despues=Decimal(str(f["capital_despues"])),
                cuotas_antes=int(f["cuotas_antes"]),
                cuotas_despues=int(f["cuotas_despues"]),
                intereses_antes=Decimal(str(f["intereses_antes"])),
                intereses_despues=Decimal(str(f["intereses_despues"])),
                detalle_json=f["detalle_json"],
            )
            for f in filas
        )

    def imputaciones_capital(
        self, prestamo_id: int
    ) -> tuple[ImputacionCapitalDetalleLectura, ...]:
        filas = self._db.consultar(
            """
            SELECT
                p.id AS pago_id,
                p.fecha_valor,
                p.tipo_pago,
                i.monto
            FROM pagos p
            JOIN imputaciones i ON i.pago_id = p.id
            WHERE p.prestamo_id = ?
              AND p.estado = 'VALIDA'
              AND i.concepto = ?
            ORDER BY p.fecha_valor, p.id, i.id
            """,
            (prestamo_id, ConceptoImputacion.CAPITAL.value),
        )
        return tuple(
            ImputacionCapitalDetalleLectura(
                pago_id=int(f["pago_id"]),
                fecha_valor=date.fromisoformat(f["fecha_valor"]),
                tipo_pago=f["tipo_pago"],
                monto=Decimal(str(f["monto"])),
            )
            for f in filas
        )
