"""
Excepciones específicas de la capa de datos.

Estas excepciones NO son lo mismo que las del dominio. El dominio
habla de reglas financieras (saldo negativo, capital insuficiente).
La infraestructura habla de problemas técnicos (base corrupta, no se
pudo abrir el archivo, transacción bloqueada).

Mantenerlas separadas permite que la capa de aplicación sepa cómo
reaccionar: un error de dominio se muestra al usuario, un error de
base de datos se loguea y se escala.
"""


class ErrorBaseDatos(Exception):
    """Base de todos los errores de la capa de datos."""


class ErrorConexion(ErrorBaseDatos):
    """
    No se pudo abrir o cerrar la base de datos.

    Puede pasar por permisos, por ruta inválida, o porque otro
    proceso tiene un lock exclusivo.
    """


class ErrorIntegridad(ErrorBaseDatos):
    """
    La verificación de integridad falló.

    Significa que la base está corrupta o que hay referencias
    rotas. Es un error grave: no se debe operar sobre una base
    que no pasa esta verificación.
    """


class ErrorTransaccion(ErrorBaseDatos):
    """
    Una transacción no pudo completarse.

    Se levanta cuando hay un error durante una operación que
    debería ser atómica, y se hace rollback.
    """


class ErrorMigracion(ErrorBaseDatos):
    """Un problema al aplicar migraciones de schema."""

class ErrorBackup(ErrorBaseDatos):
    """Un problema al crear o verificar un backup."""


class ErrorRestore(ErrorBaseDatos):
    """Un problema al restaurar o verificar un backup."""
