"""Repositorio append-only de ejecuciones SOMBRA V3."""
from __future__ import annotations

from datetime import datetime
import json

from aplicacion.servicios.puente_motor_pago_v3 import EjecucionSombraMotorPagoV3


class EjecucionesSombraV3Repo:
    """Persiste todas las ejecuciones sombra, incluidas las coincidentes."""

    def __init__(self, db) -> None:
        self.db = db

    def registrar(self, ejecucion: EjecucionSombraMotorPagoV3) -> int:
        detalle = json.dumps(
            {
                "fingerprint": ejecucion.fingerprint,
                "prestamo_id": ejecucion.prestamo_id,
                "pago_legacy_id": ejecucion.pago_legacy_id,
                "resultado": ejecucion.resultado.value,
                "revision_snapshot": ejecucion.revision_snapshot,
                "resumen": ejecucion.resumen,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        ahora = datetime.now().isoformat(timespec="seconds")
        with self.db.transaccion():
            self.db.ejecutar(
                """
                INSERT INTO ejecuciones_sombra_v3
                (prestamo_id, pago_legacy_id, fingerprint, resultado,
                 revision_snapshot, resumen, detalle_json, motor_version, creado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'V3-SOMBRA', ?)
                """,
                (
                    ejecucion.prestamo_id,
                    ejecucion.pago_legacy_id,
                    ejecucion.fingerprint,
                    ejecucion.resultado.value,
                    ejecucion.revision_snapshot,
                    ejecucion.resumen,
                    detalle,
                    ahora,
                ),
            )
            return self.db.ultimo_id_insertado()

    def por_prestamo(self, prestamo_id: int) -> list[dict]:
        return self.db.consultar(
            """SELECT *
               FROM ejecuciones_sombra_v3
               WHERE prestamo_id = ?
               ORDER BY id""",
            (prestamo_id,),
        )

    def por_resultado(self, resultado: str) -> list[dict]:
        return self.db.consultar(
            """SELECT *
               FROM ejecuciones_sombra_v3
               WHERE resultado = ?
               ORDER BY id""",
            (resultado,),
        )

    def por_fingerprint(self, fingerprint: str) -> list[dict]:
        return self.db.consultar(
            """SELECT *
               FROM ejecuciones_sombra_v3
               WHERE fingerprint = ?
               ORDER BY id""",
            (fingerprint,),
        )
