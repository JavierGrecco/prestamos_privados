"""Servicio de aplicación para operaciones operativas desde la UI.

La UI no accede directamente a SQLite ni decide políticas financieras.
Este servicio compone operaciones ya verificadas de infraestructura y las
expone como resultados simples y seguros.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from typing import Callable, TYPE_CHECKING

from aplicacion.puertos.metricas_sombra_v3 import MetricasSombraV3
from aplicacion.puertos.operacion_ui import (
    OperacionesBackup,
    ResultadoBackupOperativo,
    ResultadoIntegridadOperativa,
)
from aplicacion.servicios.preflight_motor_pago_v3 import ResultadoPreflightV3

if TYPE_CHECKING:
    from aplicacion.servicios.preflight_motor_pago_v3 import PreflightMotorPagoV3


@dataclass(frozen=True)
class ResultadoRestoreDrillUI:
    """Evidencia de un restore drill ya finalizado y limpiado."""

    ok: bool
    sha256: str
    bytes: int
    integridad_ok: bool


@dataclass(frozen=True)
class EstadoOperacionUI:
    """Estado operativo consolidado que puede presentar Streamlit."""

    integridad: ResultadoIntegridadOperativa
    backups: tuple[Path, ...]
    metricas_sombra: MetricasSombraV3
    preflight: ResultadoPreflightV3


class ServicioOperacionUI:
    """Frontera operativa segura para Streamlit."""

    def __init__(
        self,
        ruta_base_datos: str | Path,
        *,
        preflight: PreflightMotorPagoV3,
        obtener_metricas_sombra: Callable[..., MetricasSombraV3],
        operaciones_backup: OperacionesBackup,
    ) -> None:
        """Coordina operaciones mediante puertos; no conoce BaseDatos ni SQLite."""
        self._ruta_base_datos = Path(ruta_base_datos).resolve()
        self._preflight = preflight
        self._obtener_metricas_sombra = obtener_metricas_sombra
        self._operaciones_backup = operaciones_backup

    @property
    def directorio_backups(self) -> Path:
        return self._ruta_base_datos.parent / "backups"

    def estado(self) -> EstadoOperacionUI:
        integridad = self._operaciones_backup.verificar_integridad_sqlite(self._ruta_base_datos)
        backups = self.listar_backups()
        return EstadoOperacionUI(
            integridad=integridad,
            backups=backups,
            metricas_sombra=self._obtener_metricas_sombra(),
            preflight=self._preflight.evaluar(),
        )

    def verificar_integridad(self) -> ResultadoIntegridadOperativa:
        return self._operaciones_backup.verificar_integridad_sqlite(self._ruta_base_datos)

    def listar_backups(self) -> tuple[Path, ...]:
        directorio = self.directorio_backups
        if not directorio.is_dir():
            return ()
        resultados = []
        for path in directorio.glob("*.db"):
            if path.is_file() and path.with_name(path.name + ".manifest.json").is_file():
                resultados.append(path)
        return tuple(sorted(resultados, key=lambda p: p.stat().st_mtime, reverse=True))

    def verificar_backup(self, path: str | Path) -> ResultadoBackupOperativo:
        return self._operaciones_backup.verificar_backup(self._ruta_backup_segura(path))

    def crear_backup(self, *, confirmar: bool = False) -> ResultadoBackupOperativo:
        if not confirmar:
            raise ValueError("La creación del backup requiere confirmación explícita")

        self.directorio_backups.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        destino = self.directorio_backups / f"prestamos-{timestamp}.db"
        return self._operaciones_backup.crear_backup_verificado(self._ruta_base_datos, destino)

    def ejecutar_restore_drill(self, path: str | Path) -> ResultadoRestoreDrillUI:
        backup = self._ruta_backup_segura(path)
        self._operaciones_backup.verificar_backup(backup)

        with tempfile.TemporaryDirectory(prefix="prestamos-restore-drill-") as tmp:
            destino = Path(tmp) / "restore.db"
            resultado = self._operaciones_backup.restaurar_backup_verificado(backup, destino)
            return ResultadoRestoreDrillUI(
                ok=resultado.integridad.ok,
                sha256=resultado.sha256,
                bytes=resultado.bytes,
                integridad_ok=resultado.integridad.ok,
            )

    def _ruta_backup_segura(self, path: str | Path) -> Path:
        candidate = Path(path).resolve()
        base = self.directorio_backups.resolve()
        if candidate.parent != base:
            raise ValueError("La operación solo admite backups del directorio operativo")
        if candidate.suffix != ".db":
            raise ValueError("La ruta del backup debe terminar en .db")
        return candidate
