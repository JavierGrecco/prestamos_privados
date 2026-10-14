"""Unidad de trabajo SQLite para operaciones atómicas de cuentas locales."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from infraestructura.db import BaseDatos
from infraestructura.excepciones import ErrorTransaccion


class UnidadTrabajoUsuariosLocalesSQLite:
    """Conserva el rollback de BaseDatos y traduce solo errores de negocio conocidos."""

    def __init__(self, db: BaseDatos) -> None:
        self._db = db

    @contextmanager
    def transaccion(self) -> Iterator[None]:
        try:
            with self._db.transaccion():
                yield
        except ErrorTransaccion as exc:
            causa = exc.__cause__
            if isinstance(causa, (ValueError, PermissionError)):
                raise causa
            raise


__all__ = ["UnidadTrabajoUsuariosLocalesSQLite"]
