"""Unidad de trabajo SQLite para operaciones atómicas de garantías."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import sqlite3

from aplicacion.puertos.garantias_prestamo import GarantiaActivaDuplicada
from infraestructura.db import BaseDatos
from infraestructura.excepciones import ErrorTransaccion


class UnidadTrabajoGarantiasSQLite:
    """Mantiene rollback y traduce el conflicto de unicidad a un error público."""

    def __init__(self, db: BaseDatos) -> None:
        self._db = db

    @contextmanager
    def transaccion(
        self, *, propagar_errores_de_negocio: bool = False
    ) -> Iterator[None]:
        try:
            with self._db.transaccion():
                yield
        except ErrorTransaccion as exc:
            causa = exc.__cause__
            if isinstance(causa, sqlite3.IntegrityError) and (
                "uq_garantia_activa_prestamo_persona" in str(causa)
                or (
                    "UNIQUE constraint failed" in str(causa)
                    and "garantias_prestamo.prestamo_id" in str(causa)
                    and "garantias_prestamo.garante_id" in str(causa)
                )
            ):
                raise GarantiaActivaDuplicada(
                    "Esa persona ya tiene una garantía activa para este préstamo."
                ) from exc
            if propagar_errores_de_negocio and isinstance(causa, ValueError):
                raise causa
            raise


__all__ = ["UnidadTrabajoGarantiasSQLite"]
