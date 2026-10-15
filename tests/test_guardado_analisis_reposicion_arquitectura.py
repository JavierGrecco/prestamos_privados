"""Guardas de arquitectura para la escritura de análisis guardados."""

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


def test_servicio_de_aplicacion_no_importa_sqlite_ni_infraestructura():
    ruta = ROOT / "aplicacion" / "servicios" / "guardar_analisis_reposicion.py"
    prohibidos = [
        modulo for modulo in _imports(ruta)
        if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}
    ]
    assert prohibidos == []


def test_puerto_de_escritura_no_depende_de_repositorios_concretos():
    ruta = ROOT / "aplicacion" / "puertos" / "guardar_analisis_reposicion.py"
    prohibidos = [
        modulo for modulo in _imports(ruta)
        if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}
    ]
    assert prohibidos == []


def test_simulador_guarda_a_traves_del_caso_de_uso_compuesto():
    ruta = ROOT / "ui" / "pagina_simulador_carencia.py"
    fuente = ruta.read_text(encoding="utf-8")
    modulos = _imports(ruta)

    assert "infraestructura.composicion.guardar_analisis_reposicion" in modulos
    assert "crear_servicio_guardado_analisis_reposicion(db).guardar(" in fuente
    assert "repo_planes = PlanesReposicionRepo(db)" not in fuente
    assert "repo_planes.crear_plan_con_snapshot" not in fuente
    assert "repo_planes.guardar_nueva_version" not in fuente
