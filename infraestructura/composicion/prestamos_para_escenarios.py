"""Punto de composición del selector de préstamos para escenarios."""

from aplicacion.consultas.prestamos_para_escenarios import (
    PrestamosParaEscenariosQuery,
)
from infraestructura.consultas.prestamos_para_escenarios import (
    PrestamosParaEscenariosSQLiteQuery,
)


def crear_consulta_prestamos_para_escenarios(
    db,
) -> PrestamosParaEscenariosQuery:
    """Conecta la consulta de aplicación con su adaptador SQLite."""
    return PrestamosParaEscenariosQuery(
        PrestamosParaEscenariosSQLiteQuery(db)
    )


__all__ = ["crear_consulta_prestamos_para_escenarios"]
