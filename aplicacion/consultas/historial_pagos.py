"""Read model auditable para historial y detalle de pagos.

No modifica datos. Reconstruye evidencia ya persistida sin volver a ejecutar
las reglas financieras.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json


@dataclass(frozen=True)
class PagoAuditable:
    id: int
    prestamo_id: int
    prestamo_numero: str
    fecha_real: date
    fecha_valor: date
    fecha_registro: str
    monto: Decimal
    moneda: str
    estado: str
    medio: str | None
    referencia: str | None
    nota: str | None
    creado_por: str | None
    tipo_pago: str
    monto_a_capital: Decimal
    intereses_ahorrados: Decimal
    cuotas_restantes_antes: int
    cuotas_restantes_despues: int
    opcion_adelanto: str | None
    motor_version: str
    plan_hash: str | None
    plan_json: str | None
    idempotency_key: str | None
    idempotency_fingerprint: str | None
    motivo_anulacion: str | None


@dataclass(frozen=True)
class EvidenciaPagoAuditable:
    pago: PagoAuditable
    imputaciones: tuple[dict, ...]
    devengamientos: tuple[dict, ...]
    ledger: tuple[dict, ...]
    auditoria: tuple[dict, ...]
    observaciones_sombra: tuple[dict, ...]
    plan: dict | None

    @property
    def correlacion_id(self) -> str | None:
        for movimiento in self.ledger:
            if movimiento.get("entidad") == "PAGO":
                return movimiento.get("correlacion_id")
        return None


class HistorialPagosQuery:
    """Consulta de solo lectura para evidencia de pagos."""

    def __init__(self, db) -> None:
        self._db = db

    def por_persona(
        self,
        persona_id: int,
        *,
        limite: int = 100,
    ) -> tuple[PagoAuditable, ...]:
        if persona_id <= 0:
            raise ValueError("persona_id debe ser positivo")
        limite = _limite(limite)

        filas = self._db.consultar(
            """
            SELECT
                p.id,
                p.prestamo_id,
                pr.numero AS prestamo_numero,
                p.fecha_real,
                p.fecha_valor,
                p.fecha_registro,
                p.monto_moneda_pago,
                p.moneda_pago,
                p.estado,
                p.medio,
                p.referencia,
                p.nota,
                p.creado_por,
                p.tipo_pago,
                p.monto_a_capital,
                p.intereses_ahorrados,
                p.cuotas_restantes_antes,
                p.cuotas_restantes_despues,
                p.opcion_adelanto,
                p.motor_version,
                p.plan_hash,
                p.plan_json,
                p.idempotency_key,
                p.idempotency_fingerprint,
                p.motivo_anulacion
            FROM pagos p
            JOIN prestamos pr ON pr.id = p.prestamo_id
            WHERE pr.deudor_id = ?
               OR EXISTS (
                    SELECT 1
                    FROM participaciones pa
                    WHERE pa.prestamo_id = p.prestamo_id
                      AND pa.inversor_id = ?
                )
            ORDER BY p.fecha_real DESC, p.id DESC
            LIMIT ?
            """,
            (persona_id, persona_id, limite),
        )
        return tuple(_fila_pago(fila) for fila in filas)

    def por_prestamo(
        self,
        prestamo_id: int,
        *,
        limite: int = 100,
    ) -> tuple[PagoAuditable, ...]:
        if prestamo_id <= 0:
            raise ValueError("prestamo_id debe ser positivo")
        limite = _limite(limite)
        filas = self._db.consultar(
            """
            SELECT
                p.id,
                p.prestamo_id,
                pr.numero AS prestamo_numero,
                p.fecha_real,
                p.fecha_valor,
                p.fecha_registro,
                p.monto_moneda_pago,
                p.moneda_pago,
                p.estado,
                p.medio,
                p.referencia,
                p.nota,
                p.creado_por,
                p.tipo_pago,
                p.monto_a_capital,
                p.intereses_ahorrados,
                p.cuotas_restantes_antes,
                p.cuotas_restantes_despues,
                p.opcion_adelanto,
                p.motor_version,
                p.plan_hash,
                p.plan_json,
                p.idempotency_key,
                p.idempotency_fingerprint,
                p.motivo_anulacion
            FROM pagos p
            JOIN prestamos pr ON pr.id = p.prestamo_id
            WHERE p.prestamo_id = ?
            ORDER BY p.fecha_real DESC, p.id DESC
            LIMIT ?
            """,
            (prestamo_id, limite),
        )
        return tuple(_fila_pago(fila) for fila in filas)

    def detalle(self, pago_id: int) -> EvidenciaPagoAuditable | None:
        if pago_id <= 0:
            raise ValueError("pago_id debe ser positivo")

        fila = self._db.consultar_uno(
            """
            SELECT
                p.id,
                p.prestamo_id,
                pr.numero AS prestamo_numero,
                p.fecha_real,
                p.fecha_valor,
                p.fecha_registro,
                p.monto_moneda_pago,
                p.moneda_pago,
                p.estado,
                p.medio,
                p.referencia,
                p.nota,
                p.creado_por,
                p.tipo_pago,
                p.monto_a_capital,
                p.intereses_ahorrados,
                p.cuotas_restantes_antes,
                p.cuotas_restantes_despues,
                p.opcion_adelanto,
                p.motor_version,
                p.plan_hash,
                p.plan_json,
                p.idempotency_key,
                p.idempotency_fingerprint,
                p.motivo_anulacion
            FROM pagos p
            JOIN prestamos pr ON pr.id = p.prestamo_id
            WHERE p.id = ?
            """,
            (pago_id,),
        )
        if fila is None:
            return None

        pago = _fila_pago(fila)
        imputaciones = tuple(
            dict(f)
            for f in self._db.consultar(
                """
                SELECT id, pago_id, cuota_id, concepto, monto, creado_en,
                       origen, referencias_devengamiento
                FROM imputaciones
                WHERE pago_id = ?
                ORDER BY id
                """,
                (pago_id,),
            )
        )

        referencias = _referencias_devengamiento(imputaciones)
        if referencias:
            placeholders = ",".join("?" for _ in referencias)
            filas_dev = self._db.consultar(
                f"""
                SELECT *
                FROM devengamientos
                WHERE referencia IN ({placeholders})
                ORDER BY fecha_hasta, id
                """,
                tuple(referencias),
            )
        else:
            filas_dev = self._db.consultar(
                """
                SELECT *
                FROM devengamientos
                WHERE prestamo_id = ?
                  AND fecha_hasta = ?
                ORDER BY id
                """,
                (pago.prestamo_id, pago.fecha_valor.isoformat()),
            )

        devengamientos = tuple(dict(f) for f in filas_dev)

        ledger = tuple(
            dict(f)
            for f in self._db.consultar(
                """
                SELECT id, entidad, entidad_id, tipo_movimiento, debe, haber,
                       fecha, metadata, correlacion_id, creado_en
                FROM ledger
                WHERE correlacion_id = (
                    SELECT correlacion_id
                    FROM ledger
                    WHERE entidad = 'PAGO' AND entidad_id = ?
                    ORDER BY id
                    LIMIT 1
                )
                ORDER BY id
                """,
                (pago_id,),
            )
        )

        correlacion_id = next(
            (
                str(f["correlacion_id"])
                for f in ledger
                if f["entidad"] == "PAGO"
            ),
            None,
        )

        if correlacion_id is None:
            auditoria = tuple(
                dict(f)
                for f in self._db.consultar(
                    """
                    SELECT id, fecha, usuario, operacion, entidad, entidad_id,
                           datos_anteriores, datos_nuevos, motivo, correlacion_id
                    FROM auditoria
                    WHERE datos_nuevos LIKE ?
                    ORDER BY id
                    """,
                    (f'%"pago_id": {pago_id}%,' ,),
                )
            )
        else:
            auditoria = tuple(
                dict(f)
                for f in self._db.consultar(
                    """
                    SELECT id, fecha, usuario, operacion, entidad, entidad_id,
                           datos_anteriores, datos_nuevos, motivo, correlacion_id
                    FROM auditoria
                    WHERE correlacion_id = ?
                    ORDER BY id
                    """,
                    (correlacion_id,),
                )
            )

        observaciones = tuple(
            dict(f)
            for f in self._db.consultar(
                """
                SELECT id, prestamo_id, pago_legacy_id, fingerprint, tipo,
                       resumen, detalle_json, correlacion_id, motor_version,
                       creado_en
                FROM observaciones_sombra_v3
                WHERE pago_legacy_id = ?
                ORDER BY id
                """,
                (pago_id,),
            )
        )

        plan = _plan_desde_json(pago.plan_json)

        return EvidenciaPagoAuditable(
            pago=pago,
            imputaciones=imputaciones,
            devengamientos=devengamientos,
            ledger=ledger,
            auditoria=auditoria,
            observaciones_sombra=observaciones,
            plan=plan,
        )


def _fila_pago(fila) -> PagoAuditable:
    return PagoAuditable(
        id=int(fila["id"]),
        prestamo_id=int(fila["prestamo_id"]),
        prestamo_numero=str(fila["prestamo_numero"]),
        fecha_real=date.fromisoformat(fila["fecha_real"]),
        fecha_valor=date.fromisoformat(fila["fecha_valor"]),
        fecha_registro=str(fila["fecha_registro"]),
        monto=Decimal(str(fila["monto_moneda_pago"])),
        moneda=str(fila["moneda_pago"]),
        estado=str(fila["estado"]),
        medio=fila["medio"],
        referencia=fila["referencia"],
        nota=fila["nota"],
        creado_por=fila["creado_por"],
        tipo_pago=str(fila["tipo_pago"] or "CUOTA"),
        monto_a_capital=Decimal(str(fila["monto_a_capital"] or "0")),
        intereses_ahorrados=Decimal(str(fila["intereses_ahorrados"] or "0")),
        cuotas_restantes_antes=int(fila["cuotas_restantes_antes"] or 0),
        cuotas_restantes_despues=int(fila["cuotas_restantes_despues"] or 0),
        opcion_adelanto=fila["opcion_adelanto"],
        motor_version=str(fila["motor_version"] or "LEGACY"),
        plan_hash=fila["plan_hash"],
        plan_json=fila["plan_json"],
        idempotency_key=fila["idempotency_key"],
        idempotency_fingerprint=fila["idempotency_fingerprint"],
        motivo_anulacion=fila["motivo_anulacion"],
    )


def _referencias_devengamiento(imputaciones: tuple[dict, ...]) -> tuple[str, ...]:
    referencias: list[str] = []
    for imputacion in imputaciones:
        raw = imputacion.get("referencias_devengamiento")
        if not raw:
            continue
        try:
            valores = json.loads(str(raw))
        except (TypeError, ValueError):
            continue
        if isinstance(valores, list):
            referencias.extend(str(v) for v in valores if v)
    return tuple(dict.fromkeys(referencias))


def _plan_desde_json(plan_json: str | None) -> dict | None:
    if not plan_json:
        return None
    try:
        payload = json.loads(plan_json)
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _limite(limite: int) -> int:
    if limite <= 0:
        raise ValueError("El límite debe ser positivo")
    return min(limite, 500)
