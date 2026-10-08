"""Paquete de decisión para canary V3.

Compone verificaciones existentes de backup e readiness. Es solo lectura sobre
la base y no cambia el modo del motor ni ejecuta operaciones financieras.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal

from aplicacion.servicios.precheck_canary_motor_pago_v3 import (
    ResultadoReadinessCanaryV3,
    ServicioReadinessCanaryV3,
)
from infraestructura.backup import ResultadoBackup, verificar_backup


@dataclass(frozen=True)
class PaqueteCanaryV3:
    formato: int
    evaluador: str
    evaluado_en: str
    base: str
    backup: str
    backup_sha256: str
    backup_bytes: int
    backup_integridad_ok: bool
    readiness: ResultadoReadinessCanaryV3
    operador: str
    motivo_revision: str
    apto_para_revision_humana: bool

    def a_dict(self) -> dict:
        data = asdict(self)
        data["readiness"]["motivos_rechazo"] = list(
            self.readiness.motivos_rechazo
        )
        data["readiness"]["tasa_coincidencia"] = (
            None
            if self.readiness.tasa_coincidencia is None
            else str(self.readiness.tasa_coincidencia)
        )
        return data


class ServicioPaqueteCanaryV3:
    """Genera una evidencia compuesta sin efectos colaterales financieros."""

    def __init__(self, db) -> None:
        self._db = db

    def evaluar(
        self,
        *,
        base_path: str | Path,
        backup_path: str | Path,
        operador: str,
        motivo_revision: str,
        ejecuciones_minimas: int = 100,
        tasa_coincidencia_minima: Decimal = Decimal("1"),
        divergencias_maximas: int = 0,
        errores_maximos: int = 0,
    ) -> PaqueteCanaryV3:
        base = Path(base_path).resolve()
        backup = Path(backup_path).resolve()

        operador_limpio = operador.strip()
        motivo_limpio = motivo_revision.strip()
        if not operador_limpio:
            raise ValueError("Se requiere un operador para la revisión")
        if not motivo_limpio:
            raise ValueError("Se requiere un motivo para la revisión")

        evidencia_backup = verificar_backup(backup)
        readiness = ServicioReadinessCanaryV3(
            self._db,
            ejecuciones_minimas=ejecuciones_minimas,
            tasa_coincidencia_minima=tasa_coincidencia_minima,
            divergencias_maximas=divergencias_maximas,
            errores_maximos=errores_maximos,
        ).evaluar()

        apto = evidencia_backup.integridad.ok and readiness.listo
        return PaqueteCanaryV3(
            formato=1,
            evaluador="paquete_decision_canary_v3",
            evaluado_en=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            base=str(base),
            backup=str(backup),
            backup_sha256=evidencia_backup.sha256,
            backup_bytes=evidencia_backup.bytes,
            backup_integridad_ok=evidencia_backup.integridad.ok,
            readiness=readiness,
            operador=operador_limpio,
            motivo_revision=motivo_limpio,
            apto_para_revision_humana=apto,
        )
