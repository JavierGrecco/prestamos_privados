"""Composición del caso de uso para registrar aportes de reposición."""

from aplicacion.servicios.registrar_aporte_reposicion import (
    ServicioRegistrarAporteReposicion,
)
from infraestructura.consultas.registro_aporte_reposicion import (
    RegistroAporteReposicionSQLite,
)


def crear_servicio_registrar_aporte_reposicion(
    db,
) -> ServicioRegistrarAporteReposicion:
    """Conecta el caso de uso con el repositorio local existente."""
    return ServicioRegistrarAporteReposicion(RegistroAporteReposicionSQLite(db))


__all__ = ["crear_servicio_registrar_aporte_reposicion"]
