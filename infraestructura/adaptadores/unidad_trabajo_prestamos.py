"""Unidad de trabajo SQLite para el alta y ciclo de vida del préstamo."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from infraestructura.db import BaseDatos


class UnidadTrabajoPrestamosSQLite:
    """Conserva el comportamiento transaccional existente de BaseDatos."""

    def __init__(self, db: BaseDatos) -> None:
        self._db = db

    @contextmanager
    def transaccion(self) -> Iterator[None]:
        with self._db.transaccion():
            yield


__all__ = ["UnidadTrabajoPrestamosSQLite"]
