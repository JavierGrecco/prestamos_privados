"""
Servicios de aplicación.

Cada servicio encapsula un grupo de casos de uso relacionados.
"""
from .prestamos import ServicioPrestamos
from .pagos import ServicioPagos as _ServicioPagosBase
from .pagos_simulacion import ServicioPagosConSimulacion
from .registro_pago_ui import (
    ServicioRegistroPagoUI,
    ResultadoPagoUI,
    EstadoMotorPagoUI,
)
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
    "ServicioPagos",
    "ServicioPagosConSimulacion",
    "ErrorServicio",
    "ErrorDatosInvalidos",
    "ErrorEstadoInvalido",
    "ServicioRegistroPagoUI",
    "ResultadoPagoUI",
    "EstadoMotorPagoUI",
]
