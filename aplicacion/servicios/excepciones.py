"""
Excepciones de la capa de aplicación.

Son distintas de las del dominio (que hablan de reglas financieras)
y de las de infraestructura (que hablan de problemas técnicos).
Las de aplicación hablan de reglas de negocio y validaciones.
"""


class ErrorServicio(Exception):
    """Base de todos los errores de servicios de aplicación."""


class ErrorDatosInvalidos(ErrorServicio):
    """
    Los datos de entrada al servicio no son válidos.

    Ejemplo: crear un préstamo sin participaciones, o con
    porcentajes que no suman 1.
    """


class ErrorEstadoInvalido(ErrorServicio):
    """
    La operación no es válida en el estado actual de la entidad.

    Ejemplo: intentar registrar un pago sobre un préstamo cancelado,
    o cambiar la tasa de un préstamo finalizado.
    """