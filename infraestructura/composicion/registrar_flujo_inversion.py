"""Composición del caso de uso para registrar flujos de inversión."""

from aplicacion.servicios.registrar_flujo_inversion import (
    ServicioRegistrarFlujoInversion,
)
from infraestructura.consultas.registro_flujo_inversion import (
    RegistroFlujoInversionSQLite,
)


def crear_servicio_registrar_flujo_inversion(
    db,
) -> ServicioRegistrarFlujoInversion:
    """Conecta el caso de uso con la persistencia SQLite ya existente."""
    return ServicioRegistrarFlujoInversion(RegistroFlujoInversionSQLite(db))


__all__ = ["crear_servicio_registrar_flujo_inversion"]
