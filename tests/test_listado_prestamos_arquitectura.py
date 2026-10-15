"""Guardas de arquitectura para el listado de préstamos."""
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _imports(ruta: Path) -> list[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    modulos = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.extend(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.append(nodo.module)
    return modulos


def test_consulta_de_aplicacion_no_importa_sqlite_ni_infraestructura():
    ruta = ROOT / "aplicacion" / "consultas" / "listado_prestamos.py"
    prohibidos = [
        modulo
        for modulo in _imports(ruta)
        if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}
    ]
    assert prohibidos == []


def test_listado_ui_usa_fabrica_publica_y_no_consulta_repositorios():
    ruta = ROOT / "ui" / "pagina_prestamos.py"
    fuente = ruta.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(ruta))
    funcion = next(
        nodo
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.FunctionDef)
        and nodo.name == "_prestamos_de_persona"
    )
    bloque = ast.get_source_segment(fuente, funcion)

    assert "infraestructura.composicion.listado_prestamos" in _imports(ruta)
    assert "crear_consulta_listado_prestamos(db).por_persona" in bloque
    assert "PrestamoRepo" not in bloque
    assert "ParticipacionRepo" not in bloque
    assert "_proxima_cuota" not in fuente
