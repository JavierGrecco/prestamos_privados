"""Punto de composición del listado de préstamos."""

from aplicacion.consultas.listado_prestamos import ConsultaListadoPrestamos
from infraestructura.consultas.listado_prestamos import ListadoPrestamosSQLite


def crear_consulta_listado_prestamos(db) -> ConsultaListadoPrestamos:
    """Conecta el caso de lectura con su adaptador SQLite."""
    return ConsultaListadoPrestamos(ListadoPrestamosSQLite(db))


__all__ = ["crear_consulta_listado_prestamos"]
