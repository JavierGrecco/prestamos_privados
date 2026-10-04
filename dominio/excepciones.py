"""
Excepciones del dominio financiero.

¿Por qué crear excepciones propias en lugar de usar ValueError y demás?

Porque el dominio financiero tiene errores específicos que se manejan
distinto según la capa. Una validación de input se muestra al usuario.
Un error de invariante financiera es un bug que hay que loguear con
prioridad alta. Un error de cálculo puede indicar datos corruptos.

Al tener una jerarquía propia, la capa de aplicación y la UI pueden
distinguir y actuar de forma distinta según el tipo.
"""


class ErrorPrestamos(Exception):
    """Base de todas las excepciones del dominio. Se puede usar para
    capturar cualquier error de negocio sin atrapar errores de Python."""


class ErrorValidacion(ErrorPrestamos):
    """
    Los datos de entrada no son válidos.

    Ejemplo: un monto negativo, un plazo de 0 meses, una fecha
    que no tiene sentido. El usuario puede corregir y reintentar.
    """


class ErrorCalculo(ErrorPrestamos):
    """
    El cálculo produjo un resultado inesperado.

    No es un error del input, sino del proceso. Puede indicar datos
    corruptos o un caso que el motor no contempla.
    """


class ErrorInvariante(ErrorCalculo):
    """
    Se violó una invariante financiera.

    Las invariantes son condiciones que SIEMPRE deben cumplirse:
      - El saldo de un préstamo nunca puede ser negativo.
      - La suma de las imputaciones de un pago debe ser igual al pago.
      - La suma de las participaciones activas debe ser 100%.

    Si alguna se rompe, es un bug grave. No se muestra al usuario
    en lenguaje amigable; se loguea con prioridad alta.
    """


class ErrorCapitalInsuficiente(ErrorPrestamos):
    """La suma de los aportes no alcanza el capital del préstamo."""


class ErrorTasaFueraDeRango(ErrorPrestamos):
    """La tasa excede los límites configurados o razonables."""