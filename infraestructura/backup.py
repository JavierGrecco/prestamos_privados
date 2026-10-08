"""Operaciones verificables de integridad, backup y restore para SQLite.

Esta capa es operativa: no conoce reglas financieras ni decide cómo se
registran pagos. Su responsabilidad es producir artefactos recuperables y
evidencia verificable de que esos artefactos pueden abrirse correctamente.

Principios:
- nunca sobrescribir una base existente al crear un backup o un restore;
- usar la API online backup de SQLite para obtener una copia consistente aun
  cuando la fuente esté en WAL;
- validar integridad estructural y foreign keys antes de considerar válido un
  artefacto;
- acompañar cada backup con un manifiesto SHA-256;
- fallar de forma explícita ante cualquier inconsistencia operativa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import os
import shutil
import sqlite3
import tempfile

from .excepciones import ErrorBackup, ErrorRestore

LOGGER = logging.getLogger(__name__)
FORMATO_MANIFIESTO = 1


@dataclass(frozen=True)
class ResultadoIntegridad:
    """Resultado reproducible de los chequeos de una base SQLite."""

    ruta: Path
    quick_check: tuple[str, ...]
    integrity_check: tuple[str, ...]
    foreign_key_errores: tuple[tuple[object, ...], ...]

    @property
    def ok(self) -> bool:
        return (
            self.quick_check == ("ok",)
            and self.integrity_check == ("ok",)
            and not self.foreign_key_errores
        )


@dataclass(frozen=True)
class ResultadoBackup:
    """Evidencia de un backup creado y verificado."""

    ruta_backup: Path
    ruta_manifest: Path
    sha256: str
    bytes: int
    integridad: ResultadoIntegridad


@dataclass(frozen=True)
class ResultadoRestore:
    """Evidencia de un restore realizado sobre una ruta nueva."""

    ruta_restore: Path
    sha256: str
    bytes: int
    integridad: ResultadoIntegridad


def verificar_integridad_sqlite(ruta: str | Path) -> ResultadoIntegridad:
    """Ejecuta quick_check, integrity_check y foreign_key_check.

    No utiliza BaseDatos para evitar efectos operativos como crear la carpeta
    de la base o cambiar su configuración al auditar un artefacto.
    """
    path = Path(ruta)
    if not path.is_file():
        raise ErrorBackup(f"No existe la base SQLite: {path}")

    try:
        conexion = sqlite3.connect(path, timeout=5)
        try:
            conexion.execute("PRAGMA busy_timeout = 5000")
            quick = tuple(
                str(fila[0]) for fila in conexion.execute("PRAGMA quick_check")
            )
            integrity = tuple(
                str(fila[0])
                for fila in conexion.execute("PRAGMA integrity_check")
            )
            foreign_keys = tuple(
                tuple(fila)
                for fila in conexion.execute("PRAGMA foreign_key_check")
            )
        finally:
            conexion.close()
    except sqlite3.Error as exc:
        raise ErrorBackup(
            f"No se pudo verificar la integridad de {path}: {exc}"
        ) from exc

    resultado = ResultadoIntegridad(
        ruta=path,
        quick_check=quick,
        integrity_check=integrity,
        foreign_key_errores=foreign_keys,
    )
    if not resultado.ok:
        raise ErrorBackup(
            "La base no supera los chequeos de integridad: "
            f"quick_check={resultado.quick_check}, "
            f"integrity_check={resultado.integrity_check}, "
            f"foreign_keys={len(resultado.foreign_key_errores)}"
        )
    return resultado


def crear_backup_verificado(
    ruta_origen: str | Path,
    ruta_backup: str | Path,
) -> ResultadoBackup:
    """Crea un backup SQLite autocontenido, hash y manifiesto.

    La copia se realiza mediante Connection.backup(), que trabaja con el
    snapshot consistente que SQLite expone aunque la fuente esté en WAL.

    La ruta destino debe no existir. Esto evita sobrescrituras accidentales.
    """
    origen = Path(ruta_origen).resolve(strict=True)
    destino = Path(ruta_backup).absolute()

    if not origen.is_file():
        raise ErrorBackup(f"La ruta de origen no es un archivo: {origen}")
    if destino == origen:
        raise ErrorBackup("El backup no puede apuntar a la base de origen")
    if destino.exists():
        raise ErrorBackup(f"El backup destino ya existe: {destino}")

    manifest = _ruta_manifest(destino)
    if manifest.exists():
        raise ErrorBackup(f"El manifiesto destino ya existe: {manifest}")

    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal_db = Path(_temporal_en(destino.parent, destino.name))
    temporal_manifest = Path(_temporal_en(destino.parent, manifest.name))
    destino_publicado = False

    try:
        with sqlite3.connect(origen, timeout=5) as origen_db:
            origen_db.execute("PRAGMA busy_timeout = 5000")
            with sqlite3.connect(temporal_db, timeout=5) as destino_db:
                origen_db.backup(destino_db)
                destino_db.commit()

        integridad = verificar_integridad_sqlite(temporal_db)
        sha256 = _sha256(temporal_db)
        bytes_totales = temporal_db.stat().st_size

        _escribir_manifest(
            temporal_manifest,
            ruta_backup=destino,
            sha256=sha256,
            bytes_totales=bytes_totales,
        )

        _publicar_sin_sobrescribir(temporal_db, destino)
        destino_publicado = True
        _publicar_sin_sobrescribir(temporal_manifest, manifest)

    except (OSError, sqlite3.Error, ErrorBackup, ValueError, TypeError) as exc:
        if destino_publicado:
            _borrar_si_generado(destino)
            _borrar_si_generado(manifest)
        raise ErrorBackup(
            f"No se pudo crear el backup {destino}: {exc}"
        ) from exc
    finally:
        _borrar_si_generado(temporal_db)
        _borrar_si_generado(temporal_manifest)

    LOGGER.info(
        "Backup SQLite creado y verificado: path=%s bytes=%d sha256=%s",
        destino,
        bytes_totales,
        sha256,
    )
    return ResultadoBackup(
        ruta_backup=destino,
        ruta_manifest=manifest,
        sha256=sha256,
        bytes=bytes_totales,
        integridad=integridad,
    )


def verificar_backup(ruta_backup: str | Path) -> ResultadoBackup:
    """Verifica manifiesto, hash, tamaño e integridad de un backup."""
    backup = Path(ruta_backup).resolve(strict=True)
    manifest = _ruta_manifest(backup)

    if not manifest.is_file():
        raise ErrorBackup(f"Falta el manifiesto del backup: {manifest}")

    try:
        datos = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ErrorBackup(f"Manifiesto inválido: {manifest}") from exc

    if datos.get("formato") != FORMATO_MANIFIESTO:
        raise ErrorBackup(
            f"Formato de manifiesto no soportado: {datos.get('formato')}"
        )

    esperado_sha = datos.get("sha256")
    esperado_bytes = datos.get("bytes")
    if not isinstance(esperado_sha, str) or not esperado_sha:
        raise ErrorBackup("El manifiesto no contiene un SHA-256 válido")
    if not isinstance(esperado_bytes, int) or esperado_bytes < 0:
        raise ErrorBackup("El manifiesto no contiene un tamaño válido")

    bytes_reales = backup.stat().st_size
    sha_reales = _sha256(backup)
    if bytes_reales != esperado_bytes:
        raise ErrorBackup(
            f"Tamaño del backup no coincide: esperado={esperado_bytes}, "
            f"observado={bytes_reales}"
        )
    if sha_reales != esperado_sha:
        raise ErrorBackup("El SHA-256 del backup no coincide con su manifiesto")

    integridad = verificar_integridad_sqlite(backup)
    return ResultadoBackup(
        ruta_backup=backup,
        ruta_manifest=manifest,
        sha256=sha_reales,
        bytes=bytes_reales,
        integridad=integridad,
    )


def restaurar_backup_verificado(
    ruta_backup: str | Path,
    ruta_restore: str | Path,
) -> ResultadoRestore:
    """Restaura un backup a una ruta nueva y valida la copia resultante.

    No sobrescribe destinos existentes. Sirve para una restauración real a una
    ruta vacía y para un restore drill automatizado.
    """
    backup = Path(ruta_backup).resolve(strict=True)
    restore = Path(ruta_restore).absolute()

    if restore == backup:
        raise ErrorRestore("El restore no puede apuntar al propio backup")
    if restore.exists():
        raise ErrorRestore(f"La ruta de restore ya existe: {restore}")

    evidencia = verificar_backup(backup)
    restore.parent.mkdir(parents=True, exist_ok=True)
    temporal = Path(_temporal_en(restore.parent, restore.name))
    publicado = False

    try:
        shutil.copyfile(backup, temporal)
        with temporal.open("rb+") as archivo:
            archivo.flush()
            os.fsync(archivo.fileno())

        if _sha256(temporal) != evidencia.sha256:
            raise ErrorRestore("El archivo restaurado no conserva el SHA-256")

        _publicar_sin_sobrescribir(temporal, restore)
        publicado = True

        integridad = verificar_integridad_sqlite(restore)
    except (
        OSError,
        ErrorBackup,
        ErrorRestore,
        ValueError,
        TypeError,
    ) as exc:
        if publicado:
            _borrar_si_generado(restore)
        raise ErrorRestore(
            f"No se pudo restaurar el backup en {restore}: {exc}"
        ) from exc
    finally:
        _borrar_si_generado(temporal)

    LOGGER.info(
        "Restore SQLite verificado: path=%s bytes=%d sha256=%s",
        restore,
        evidencia.bytes,
        evidencia.sha256,
    )
    return ResultadoRestore(
        ruta_restore=restore,
        sha256=evidencia.sha256,
        bytes=evidencia.bytes,
        integridad=integridad,
    )


def _ruta_manifest(backup: Path) -> Path:
    return backup.with_name(backup.name + ".manifest.json")


def _sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _temporal_en(directorio: Path, nombre: str) -> str:
    fd, ruta = tempfile.mkstemp(
        prefix=f".{nombre}.",
        suffix=".tmp",
        dir=directorio,
    )
    os.close(fd)
    return ruta


def _escribir_manifest(
    ruta: Path,
    *,
    ruta_backup: Path,
    sha256: str,
    bytes_totales: int,
) -> None:
    payload = {
        "formato": FORMATO_MANIFIESTO,
        "backup": ruta_backup.name,
        "bytes": bytes_totales,
        "sha256": sha256,
        "creado_en": datetime.now(timezone.utc).isoformat(),
    }
    ruta.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with ruta.open("rb+") as archivo:
        archivo.flush()
        os.fsync(archivo.fileno())


def _publicar_sin_sobrescribir(origen: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    os.link(origen, destino)


def _borrar_si_generado(ruta: Path) -> None:
    try:
        ruta.unlink(missing_ok=True)
    except OSError:
        LOGGER.exception(
            "No se pudo limpiar un artefacto temporal: %s", ruta
        )
