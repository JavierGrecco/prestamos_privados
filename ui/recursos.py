"""Ciclo de vida de recursos propios de una sesión Streamlit."""

from __future__ import annotations


def liberar_recurso_db(recurso: object) -> None:
    """Cierra una conexión SQLite cuando Streamlit libera una sesión.

    La UI recibe la base mediante la composición de infraestructura y no
    importa la clase concreta. El contrato mínimo del recurso es exponer
    `cerrar()`, operación idempotente y protegida por el lock de BaseDatos.
    """
    cerrar = getattr(recurso, "cerrar", None)
    if not callable(cerrar):
        raise TypeError(
            "El recurso de base de datos debe implementar el método cerrar()."
        )
    cerrar()
