"""Contratos de error: los consumidores no dependen de excepciones SQLite."""

import ast
from pathlib import Path

from aplicacion.puertos.errores_persistencia import (
    ErrorPersistencia,
    ErrorUnidadTrabajo,
)
from infraestructura.excepciones import ErrorBaseDatos, ErrorTransaccion


ROOT = Path(__file__).resolve().parents[1]
CONSUMIDORES = (
    "aplicacion/servicios/pagos.py",
    "ui/pagina_operacion.py",
    "ui/pagina_proponer_correccion_auditable.py",
    "ui/pagina_registrar_pago.py",
)


def test_errores_sqlite_implementan_los_contratos_de_aplicacion():
    """Los tipos concretos conservan compatibilidad y cumplen el puerto."""
    assert issubclass(ErrorBaseDatos, ErrorPersistencia)
    assert issubclass(ErrorTransaccion, ErrorPersistencia)
    assert issubclass(ErrorTransaccion, ErrorUnidadTrabajo)


def test_consumidores_no_importan_excepciones_concretas_de_infraestructura():
    """La interfaz y la fachada dependen de categorías estables de aplicación."""
    problemas = []
    for relativo in CONSUMIDORES:
        archivo = ROOT / relativo
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=relativo)
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) and nodo.module == "infraestructura.excepciones":
                problemas.append(f"{relativo}:{nodo.lineno} importa infraestructura.excepciones")

    assert problemas == [], "\n".join(problemas)
