"""Repositorio append-only de observaciones del modo SOMBRA V3."""
from __future__ import annotations

from datetime import datetime
import json

from aplicacion.servicios.puente_motor_pago_v3 import DivergenciaMotorPagoV3


class ObservacionesSombraV3Repo:
    """Persiste observaciones después de la operación Legacy, nunca antes."""

    def __init__(self, db) -> None:
        self.db = db

    def registrar(self, observacion: DivergenciaMotorPagoV3) -> int:
        if observacion.prestamo_id is None:
            raise ValueError("La observación SOMBRA requiere prestamo_id")

        pago_legacy_id = observacion.pago_legacy_id
        correlacion_id = None

        if pago_legacy_id is not None:
            fila = self.db.consultar_uno(
                """SELECT correlacion_id
                   FROM ledger
                   WHERE entidad = 'PAGO' AND entidad_id = ?
                   ORDER BY id
                   LIMIT 1""",
                (pago_legacy_id,),
            )
            if fila is not None:
                correlacion_id = fila["correlacion_id"]

        ahora = datetime.now().isoformat(timespec="seconds")
        detalle = json.dumps(
            {
                "fingerprint": observacion.fingerprint,
                "tipo": observacion.tipo,
                "resumen": observacion.resumen,
                "prestamo_id": observacion.prestamo_id,
                "pago_legacy_id": pago_legacy_id,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        with self.db.transaccion():
            self.db.ejecutar(
                """
                INSERT INTO observaciones_sombra_v3
                (prestamo_id, pago_legacy_id, fingerprint, tipo, resumen,
                 detalle_json, correlacion_id, motor_version, creado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'V3-SOMBRA', ?)
                """,
                (
                    observacion.prestamo_id,
                    pago_legacy_id,
                    observacion.fingerprint,
                    observacion.tipo,
                    observacion.resumen,
                    detalle,
                    correlacion_id,
                    ahora,
                ),
            )
            return self.db.ultimo_id_insertado()

    def por_prestamo(self, prestamo_id: int) -> list[dict]:
        return self.db.consultar(
            """SELECT *
               FROM observaciones_sombra_v3
               WHERE prestamo_id = ?
               ORDER BY id""",
            (prestamo_id,),
        )

    def por_fingerprint(self, fingerprint: str) -> list[dict]:
        return self.db.consultar(
            """SELECT *
               FROM observaciones_sombra_v3
               WHERE fingerprint = ?
               ORDER BY id""",
            (fingerprint,),
        )

    def por_tipo(self, tipo: str) -> list[dict]:
        return self.db.consultar(
            """SELECT *
               FROM observaciones_sombra_v3
               WHERE tipo = ?
               ORDER BY id""",
            (tipo,),
        )
