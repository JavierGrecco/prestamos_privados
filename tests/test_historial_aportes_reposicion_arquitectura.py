"""Guardas de arquitectura para la lectura del historial de aportes."""

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
    ruta = ROOT / "aplicacion" / "consultas" / "historial_aportes_reposicion.py"
    prohibidos = [
        modulo for modulo in _imports(ruta)
        if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}
    ]
    assert prohibidos == []


def test_puerto_de_aportes_no_depende_de_persistencia_concreta():
    ruta = ROOT / "aplicacion" / "puertos" / "historial_aportes_reposicion.py"
    prohibidos = [
        modulo for modulo in _imports(ruta)
        if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}
    ]
    assert prohibidos == []


def test_simulador_usa_consulta_publica_y_no_repositorio_concreto():
    ruta = ROOT / "ui" / "pagina_simulador_carencia.py"
    fuente = ruta.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(ruta))
    funcion = next(
        nodo for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.FunctionDef)
        and nodo.name == "_render_analisis_guardados"
    )
    bloque = ast.get_source_segment(fuente, funcion)
    modulos = _imports(ruta)

    assert "infraestructura.composicion.historial_aportes_reposicion" in modulos
    assert "crear_consulta_historial_aportes_reposicion(db).listar(plan.id)" in bloque
    assert "PlanesReposicionRepo" not in modulos
    assert "repo." not in bloque
