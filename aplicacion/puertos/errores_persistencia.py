"""Contratos de errores técnicos de los adaptadores de persistencia.

La aplicación y la interfaz dependen de estas categorías estables. Los
adaptadores concretos pueden añadir contexto propio, pero deben conservar
la clase de contrato para que los consumidores no conozcan SQLite.
"""


class ErrorPersistencia(Exception):
    """Un adaptador de persistencia no pudo completar una operación técnica."""


class ErrorUnidadTrabajo(ErrorPersistencia):
    """La unidad de trabajo no pudo completar una operación atómica.

    El adaptador debe revertir los cambios antes de propagar este error.
    """
