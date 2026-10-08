"""
Servicios de aplicación.

Cada servicio encapsula un grupo de casos de uso relacionados.
"""
from .prestamos import ServicioPrestamos
from .personas import ServicioPersonas
from .pagos import ServicioPagos as _ServicioPagosBase
from .pagos_simulacion import ServicioPagosConSimulacion
from .excepciones import (
    ErrorServicio,
    ErrorDatosInvalidos,
    ErrorEstadoInvalido,
)

# Se conserva el nombre público original para no romper imports existentes.
# Los consumidores siguen haciendo `from aplicacion.servicios import ServicioPagos`
# y reciben el mismo servicio, ahora con simulación previa incluida.
ServicioPagos = ServicioPagosConSimulacion

__all__ = [
    "ServicioPrestamos",
    "ServicioPersonas",
    "ServicioPagos",
    "ServicioPagosConSimulacion",
    "ErrorServicio",
    "ErrorDatosInvalidos",
    "ErrorEstadoInvalido",
]
