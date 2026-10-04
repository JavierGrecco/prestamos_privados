"""
Servicios de aplicación.

Cada servicio encapsula un grupo de casos de uso relacionados.
"""
from .prestamos import ServicioPrestamos
from .pagos import ServicioPagos
from .excepciones import (
    ErrorServicio,
    ErrorDatosInvalidos,
    ErrorEstadoInvalido,
)

__all__ = [
    "ServicioPrestamos",
    "ServicioPagos",
    "ErrorServicio",
    "ErrorDatosInvalidos",
    "ErrorEstadoInvalido",
]