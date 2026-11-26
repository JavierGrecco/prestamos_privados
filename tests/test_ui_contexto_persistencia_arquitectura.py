"""Guardas de arquitectura para el contexto de persistencia entregado a la UI."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PANTALLAS = (
    "ui/pagina_alta_prestamo.py",
    "ui/pagina_comparador.py",
    "ui/pagina_escenarios.py",
    "ui/pagina_mi_espacio.py",
    "ui/pagina_planificar.py",
    "ui/pagina_prestamos.py",
    "ui/pagina_principal.py",
    "ui/pagina_registrar_pago.py",
)


def test_pantallas_no_importan_la_base_de_datos_concreta():
    """La UI entrega el contexto a composición; no conoce el adaptador SQLite."""
    for relativo in PANTALLAS:
        archivo = ROOT / relativo
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=relativo)
        problemas = []

        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom):
                if nodo.module == "infraestructura.db":
                    problemas.append(f"línea {nodo.lineno}: importa infraestructura.db")
            if isinstance(nodo, ast.Name) and nodo.id == "BaseDatos":
                problemas.append(f"línea {nodo.lineno}: referencia BaseDatos")

        assert not problemas, (
            f"{relativo} debe tratar db como contexto opaco: " + "; ".join(problemas)
        )


def test_parametros_db_de_la_ui_tienen_anotacion_opaca():
    """Las pantallas no tipan el contexto con una clase de infraestructura."""
    total = 0
    for relativo in PANTALLAS:
        archivo = ROOT / relativo
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=relativo)
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            argumentos = (
                *nodo.args.posonlyargs,
                *nodo.args.args,
                *nodo.args.kwonlyargs,
            )
            for argumento in argumentos:
                if argumento.arg != "db":
                    continue
                total += 1
                assert isinstance(argumento.annotation, ast.Name), (
                    f"{relativo}:{nodo.lineno} debe declarar db como object"
                )
                assert argumento.annotation.id == "object", (
                    f"{relativo}:{nodo.lineno} debe tratar db como un contexto opaco"
                )
    assert total >= 8
