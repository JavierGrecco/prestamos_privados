"""Punto de composición de la consulta de ficha del préstamo."""

from aplicacion.consultas.ficha_prestamo import ConsultaFichaPrestamo
from infraestructura.consultas.ficha_prestamo import FichaPrestamoSQLite


def crear_consulta_ficha_prestamo(db) -> ConsultaFichaPrestamo:
    """Conecta la consulta de aplicación con el adaptador de lectura SQLite."""
    return ConsultaFichaPrestamo(FichaPrestamoSQLite(db))


__all__ = ["crear_consulta_ficha_prestamo"]
