"""Guardas de arquitectura para la consulta de planes guardados."""

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


def test_consulta_aplicacion_no_importa_infraestructura_ni_sqlite():
    ruta = ROOT / "aplicacion" / "consultas" / "planes_reposicion_guardados.py"
    prohibidos = [
        modulo for modulo in _imports(ruta)
        if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}
    ]
    assert prohibidos == []


def test_puerto_de_planes_guardados_no_depende_de_repositorios():
    ruta = ROOT / "aplicacion" / "puertos" / "planes_reposicion_guardados.py"
    prohibidos = [
        modulo for modulo in _imports(ruta)
        if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}
    ]
    assert prohibidos == []


def test_simulador_usa_consulta_compuesta_para_leer_plan_y_version():
    ruta = ROOT / "ui" / "pagina_simulador_carencia.py"
    fuente = ruta.read_text(encoding="utf-8")
    modulos = _imports(ruta)

    assert "infraestructura.composicion.planes_reposicion_guardados" in modulos
    assert "crear_consulta_planes_reposicion_guardados(db)" in fuente
    assert "consulta_planes.obtener_plan(int(plan_id))" in fuente
    assert "consulta_planes.listar_versiones(plan.id)" in fuente
    assert "consulta_planes.obtener_version(plan.id, int(numero))" in fuente

    # Las lecturas que verifican el snapshot ya no pasan por el repositorio
    # directo; las escrituras y los movimientos de inversión quedan fuera.
    prohibidos = (
        "repo.listar_planes",
        "repo.obtener_plan",
        "repo.listar_versiones",
        "repo.obtener_version",
        "repo.verificar_version",
        "repo_planes.listar_planes",
    )
    assert all(expresion not in fuente for expresion in prohibidos)
