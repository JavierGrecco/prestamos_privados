"""Composición del caso de uso para registrar valuaciones de inversión."""

from aplicacion.servicios.registrar_valoracion_inversion import (
    ServicioRegistrarValoracionInversion,
)
from infraestructura.consultas.registro_valoracion_inversion import (
    RegistroValoracionInversionSQLite,
)


def crear_servicio_registrar_valoracion_inversion(
    db,
) -> ServicioRegistrarValoracionInversion:
    """Conecta la operación de aplicación con la persistencia SQLite."""
    return ServicioRegistrarValoracionInversion(RegistroValoracionInversionSQLite(db))


__all__ = ["crear_servicio_registrar_valoracion_inversion"]
