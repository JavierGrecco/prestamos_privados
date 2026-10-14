"""Alias de compatibilidad para el antiguo nombre SOMBRA SQLite.

La implementación ya no vive aquí: el planificador recibe un puerto de lectura
y no depende de una base de datos concreta. Se conserva el nombre histórico
mientras se migran consumidores externos.
"""

from aplicacion.servicios.planificador_sombra_pago_v3 import (
    PlanificadorSombraPagoV3,
)

SombraPagoV3SQLite = PlanificadorSombraPagoV3

__all__ = ["SombraPagoV3SQLite"]
