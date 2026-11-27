"""Limpieza de datos financieros privados guardados solo en la sesión UI.

Los valores de Mi espacio no se persisten en SQLite. Aun así, deben eliminarse
cuando termina o se invalida la autenticación para impedir que reaparezcan si
otra cuenta inicia sesión en la misma sesión del navegador.
"""

from __future__ import annotations

from collections.abc import MutableMapping

PREFIJO_DATOS_FINANCIEROS_TEMPORALES = "mi_espacio_"


def limpiar_datos_financieros_temporales(
    estado: MutableMapping[str, object],
) -> int:
    """Elimina los valores temporales de Mi espacio y devuelve cuántos quitó.

    Se conserva el tema, la navegación y cualquier otra preferencia que no sea
    dato financiero personal. Se reciben los valores de sesión explícitamente
    para que la regla pueda probarse sin levantar Streamlit.
    """

    claves = tuple(
        clave
        for clave in estado.keys()
        if isinstance(clave, str)
        and clave.startswith(PREFIJO_DATOS_FINANCIEROS_TEMPORALES)
    )
    for clave in claves:
        estado.pop(clave, None)
    return len(claves)


__all__ = [
    "PREFIJO_DATOS_FINANCIEROS_TEMPORALES",
    "limpiar_datos_financieros_temporales",
]
