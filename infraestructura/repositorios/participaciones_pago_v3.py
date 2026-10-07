"""Infraestructura para obtener participaciones activas y distribuir un cobro."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import json

from infraestructura.db import BaseDatos
from dominio.distribucion_pago_v3 import ParticipacionPagoV3, distribuir_pago_v3
from dominio.excepciones import ErrorInvariante, ErrorValidacion
from dominio.tipos import money


class RepositorioParticipacionesPagoSQLiteV3:
    def __init__(self, db: BaseDatos) -> None:
        self.db = db

    def activas(self, prestamo_id: int) -> tuple[ParticipacionPagoV3, ...]:
        filas = self.db.consultar(
            """
            SELECT inversor_id, porcentaje
            FROM participaciones
            WHERE prestamo_id = ? AND estado = 'ACTIVA'
            ORDER BY inversor_id, id
            """,
            (prestamo_id,),
        )
        return tuple(
            ParticipacionPagoV3(
                inversor_id=int(f["inversor_id"]),
                porcentaje=Decimal(str(f["porcentaje"])),
            )
            for f in filas
        )

    def calcular_distribucion(self, prestamo_id: int, monto: Decimal):
        partes = self.activas(prestamo_id)
        if not partes:
            return tuple()
        return distribuir_pago_v3(monto, partes)

    def persistir_distribucion_sin_transaccion(
        self,
        *,
        prestamo_id: int,
        pago_id: int,
        monto: Decimal,
        fecha: date,
        correlacion_id: str,
        usuario: str,
    ) -> tuple:
        asignaciones = self.calcular_distribucion(prestamo_id, monto)
        if not asignaciones:
            return tuple()
        ahora = datetime.now().isoformat(timespec="seconds")
        movimientos = []
        for a in asignaciones:
            movimientos.append({
                "entidad": "INVERSOR", "entidad_id": a.inversor_id,
                "tipo_movimiento": "COBRO_PAGO", "debe": a.monto, "haber": Decimal("0"),
            })
            movimientos.append({
                "entidad": "PRESTAMO", "entidad_id": prestamo_id,
                "tipo_movimiento": "DISTRIBUCION_INVERSOR", "debe": Decimal("0"), "haber": a.monto,
            })
        self.db.ejecutar(
            """
            INSERT INTO auditoria
            (fecha, usuario, operacion, entidad, entidad_id, datos_anteriores, datos_nuevos, motivo, correlacion_id)
            VALUES (?, ?, 'PAGO_DISTRIBUCION_INVERSORES', 'PAGO', ?, NULL, ?, ?, ?)
            """,
            (
                ahora,
                usuario,
                pago_id,
                json.dumps(
                    {
                        "prestamo_id": prestamo_id,
                        "pago_id": pago_id,
                        "monto": str(money(monto)),
                        "asignaciones": [
                            {"inversor_id": a.inversor_id, "monto": str(a.monto)}
                            for a in asignaciones
                        ],
                    },
                    sort_keys=True, separators=(",", ":"),
                ),
                "Distribución determinista de cobro entre participaciones activas",
                correlacion_id,
            ),
        )
        for mov in movimientos:
            self.db.ejecutar(
                """
                INSERT INTO ledger
                (entidad, entidad_id, tipo_movimiento, debe, haber, fecha, metadata, correlacion_id, creado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mov["entidad"], mov["entidad_id"], mov["tipo_movimiento"],
                    str(mov["debe"]), str(mov["haber"]), fecha.isoformat(),
                    json.dumps({"pago_id": pago_id}, separators=(",", ":")),
                    correlacion_id, ahora,
                ),
            )
        return asignaciones


def correlacion_de_pago(db: BaseDatos, pago_id: int) -> str:
    fila = db.consultar_uno(
        "SELECT correlacion_id FROM ledger WHERE entidad='PAGO' AND entidad_id=? ORDER BY id LIMIT 1",
        (pago_id,),
    )
    if fila is None:
        raise ErrorInvariante(f"No existe correlación de ledger para pago {pago_id}")
    return str(fila["correlacion_id"])
