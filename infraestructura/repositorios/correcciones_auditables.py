"""Repositorio SQLite para las propuestas de corrección auditables.

La unidad de trabajo mantiene juntas la lectura del estado, la comprobación de
idempotencia y la escritura. Los servicios no ven conexiones ni sentencias SQL.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from aplicacion.puertos.correcciones_auditables import (
    CorreccionAuditable,
    NuevaCorreccionAuditable,
    ReferenciaCorreccionAuditable,
    SnapshotOriginalCorreccion,
    UltimaCorreccionAuditable,
    UnidadTrabajoCorreccionesAuditables,
)
from dominio.excepciones import ErrorValidacion
from infraestructura.db import BaseDatos
from infraestructura.excepciones import ErrorTransaccion


_TABLAS_ORIGEN = {
    "APORTE_REPOSICION": "aportes_reposicion",
    "FLUJO_INVERSION_REPOSICION": "flujos_inversion_reposicion",
    "VALUACION_INVERSION_REPOSICION": "valuaciones_inversion_reposicion",
}


def _tabla_origen(entidad_tipo: str) -> str:
    """Solo permite los tres tipos de registro autorizados para corrección."""
    tabla = _TABLAS_ORIGEN.get(entidad_tipo)
    if tabla is None:
        raise ErrorValidacion("El tipo de entidad no admite correcciones auditables")
    return tabla


def _fila_a_correccion(fila) -> CorreccionAuditable:
    return CorreccionAuditable(
        id=int(fila["id"]),
        entidad_tipo=str(fila["entidad_tipo"]),
        entidad_id=int(fila["entidad_id"]),
        hash_original=str(fila["hash_original"]),
        snapshot_corregido_json=str(fila["snapshot_corregido_json"]),
        hash_corregido=str(fila["hash_corregido"]),
        motivo=str(fila["motivo"]),
        corregido_por=str(fila["corregido_por"]),
        corregido_en_utc=str(fila["corregido_en_utc"]),
        clave_idempotencia=str(fila["clave_idempotencia"]),
        correccion_anterior_id=(
            int(fila["correccion_anterior_id"])
            if fila["correccion_anterior_id"] is not None
            else None
        ),
    )


class _UnidadTrabajoCorreccionesAuditablesSQLite:
    """Adaptador de escritura activo solo durante la transacción del repositorio."""

    def __init__(self, db: BaseDatos) -> None:
        self._db = db

    def obtener_por_clave(self, clave: str) -> CorreccionAuditable | None:
        fila = self._db.consultar_uno(
            "SELECT * FROM correcciones_auditables WHERE clave_idempotencia = ?",
            (clave,),
        )
        return _fila_a_correccion(fila) if fila is not None else None

    def obtener_snapshot_original(
        self, entidad_tipo: str, entidad_id: int
    ) -> SnapshotOriginalCorreccion | None:
        tabla = _tabla_origen(entidad_tipo)
        fila = self._db.consultar_uno(
            f"SELECT snapshot_json, snapshot_sha256 FROM {tabla} WHERE id = ?",
            (entidad_id,),
        )
        if fila is None:
            return None
        return SnapshotOriginalCorreccion(
            snapshot_json=str(fila["snapshot_json"]),
            snapshot_sha256=str(fila["snapshot_sha256"]),
        )

    def obtener_ultima_correccion(
        self, entidad_tipo: str, entidad_id: int
    ) -> UltimaCorreccionAuditable | None:
        fila = self._db.consultar_uno(
            """
            SELECT id, hash_original
            FROM correcciones_auditables
            WHERE entidad_tipo = ? AND entidad_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (entidad_tipo, entidad_id),
        )
        if fila is None:
            return None
        return UltimaCorreccionAuditable(
            id=int(fila["id"]),
            hash_original=str(fila["hash_original"]),
        )

    def insertar(
        self, propuesta: NuevaCorreccionAuditable
    ) -> CorreccionAuditable:
        self._db.ejecutar(
            """
            INSERT INTO correcciones_auditables (
                entidad_tipo, entidad_id, hash_original,
                snapshot_corregido_json, hash_corregido, motivo,
                corregido_por, corregido_en_utc, clave_idempotencia,
                correccion_anterior_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                propuesta.entidad_tipo,
                propuesta.entidad_id,
                propuesta.hash_original,
                propuesta.snapshot_corregido_json,
                propuesta.hash_corregido,
                propuesta.motivo,
                propuesta.corregido_por,
                propuesta.corregido_en_utc,
                propuesta.clave_idempotencia,
                propuesta.correccion_anterior_id,
            ),
        )
        nuevo_id = self._db.ultimo_id_insertado()
        fila = self._db.consultar_uno(
            "SELECT * FROM correcciones_auditables WHERE id = ?",
            (nuevo_id,),
        )
        if fila is None:
            raise ErrorTransaccion(
                "Se insertó una corrección pero no se pudo volver a leer"
            )
        return _fila_a_correccion(fila)


class CorreccionesAuditablesSQLiteRepository:
    """Implementación local del contrato con una transacción SQLite por propuesta."""

    def __init__(self, db: BaseDatos) -> None:
        self._db = db

    @contextmanager
    def transaccion(self) -> Iterator[UnidadTrabajoCorreccionesAuditables]:
        try:
            with self._db.transaccion(inmediata=True):
                yield _UnidadTrabajoCorreccionesAuditablesSQLite(self._db)
        except ErrorTransaccion as exc:
            # La base envuelve excepciones de negocio al revertir; exponemos de
            # nuevo el error que entiende la aplicación sin filtrar detalles SQL.
            if isinstance(exc.__cause__, ErrorValidacion):
                raise exc.__cause__ from exc
            raise

    def listar_referencias_recientes(
        self, limite: int
    ) -> tuple[ReferenciaCorreccionAuditable, ...]:
        filas = self._db.consultar(
            """
            SELECT id, entidad_tipo, entidad_id
            FROM correcciones_auditables
            ORDER BY id DESC
            LIMIT ?
            """,
            (limite,),
        )
        return tuple(
            ReferenciaCorreccionAuditable(
                id=int(fila["id"]),
                entidad_tipo=str(fila["entidad_tipo"]),
                entidad_id=int(fila["entidad_id"]),
            )
            for fila in filas
        )

    def obtener(self, propuesta_id: int) -> CorreccionAuditable | None:
        fila = self._db.consultar_uno(
            "SELECT * FROM correcciones_auditables WHERE id = ?",
            (propuesta_id,),
        )
        return _fila_a_correccion(fila) if fila is not None else None

    def listar_historial(
        self, entidad_tipo: str, entidad_id: int
    ) -> tuple[CorreccionAuditable, ...]:
        filas = self._db.consultar(
            """
            SELECT * FROM correcciones_auditables
            WHERE entidad_tipo = ? AND entidad_id = ?
            ORDER BY id
            """,
            (entidad_tipo, entidad_id),
        )
        return tuple(_fila_a_correccion(fila) for fila in filas)

    def obtener_snapshot_original(
        self, entidad_tipo: str, entidad_id: int
    ) -> SnapshotOriginalCorreccion | None:
        tabla = _tabla_origen(entidad_tipo)
        fila = self._db.consultar_uno(
            f"SELECT snapshot_json, snapshot_sha256 FROM {tabla} WHERE id = ?",
            (entidad_id,),
        )
        if fila is None:
            return None
        return SnapshotOriginalCorreccion(
            snapshot_json=str(fila["snapshot_json"]),
            snapshot_sha256=str(fila["snapshot_sha256"]),
        )


__all__ = ["CorreccionesAuditablesSQLiteRepository"]
