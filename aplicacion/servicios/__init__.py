"""
Servicios de aplicación.

Cada servicio encapsula un grupo de casos de uso relacionados.
"""
from .prestamos import ServicioPrestamos
from .personas import ServicioPersonas
from .garantias_prestamo import ServicioGarantiasPrestamo
from .exportaciones import ServicioExportaciones
from .reporte_inversion_reposicion import (
    ReporteInversionReposicion,
    ServicioReporteInversionReposicion,
)
from .correcciones_auditables import (
    CorreccionAuditable,
    ServicioCorreccionesAuditables,
)
from .auditoria import ServicioAuditoria, FiltrosAuditoria
from .configuracion_motor_pago import ServicioConfiguracionMotorPago
from .precheck_canary_motor_pago_v3 import ServicioReadinessCanaryV3, ResultadoReadinessCanaryV3
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
    "ServicioGarantiasPrestamo",
    "ServicioExportaciones",
    "ReporteInversionReposicion",
    "ServicioReporteInversionReposicion",
    "CorreccionAuditable",
    "ServicioCorreccionesAuditables",
    "ServicioAuditoria",
    "FiltrosAuditoria",
    "ServicioConfiguracionMotorPago",
    "ServicioReadinessCanaryV3",
    "ResultadoReadinessCanaryV3",
    "ServicioPagos",
    "ServicioPagosConSimulacion",
    "ErrorServicio",
    "ErrorDatosInvalidos",
    "ErrorEstadoInvalido",
]
