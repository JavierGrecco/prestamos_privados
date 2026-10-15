"""Guarda arquitectónica para la pantalla de alta de préstamo."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGINA = ROOT / "ui" / "pagina_alta_prestamo.py"


def test_alta_de_prestamo_usa_servicio_publico_para_listar_personas():
    fuente = PAGINA.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(PAGINA))

    imports_repositorios = []
    construcciones_repositorio = []
    import_composicion = False
    llamadas_por_rol = set()

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom):
            if (nodo.module or "").startswith("infraestructura.repositorios"):
                imports_repositorios.extend(alias.name for alias in nodo.names)
            if nodo.module == "infraestructura.composicion.personas":
                import_composicion = any(
                    alias.name == "crear_servicio_personas" for alias in nodo.names
                )

        if isinstance(nodo, ast.Call):
            if isinstance(nodo.func, ast.Name) and nodo.func.id.endswith("Repo"):
                construcciones_repositorio.append(nodo.func.id)
            if (
                isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "listar"
            ):
                for keyword in nodo.keywords:
                    if keyword.arg == "rol" and isinstance(keyword.value, ast.Constant):
                        llamadas_por_rol.add(keyword.value.value)

    assert not imports_repositorios
    assert not construcciones_repositorio
    assert import_composicion
    assert llamadas_por_rol == {"DEUDOR", "INVERSOR"}
