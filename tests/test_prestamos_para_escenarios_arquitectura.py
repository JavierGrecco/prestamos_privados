"""Guardas de arquitectura para el selector de préstamos de escenarios."""
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _imports(ruta: Path) -> list[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    modulos = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.extend(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.module:
                modulos.append(nodo.module)
    return modulos


def test_consulta_de_aplicacion_no_importa_sqlite_ni_infraestructura():
    ruta = ROOT / "aplicacion" / "consultas" / "prestamos_para_escenarios.py"
    prohibidos = [
        modulo
        for modulo in _imports(ruta)
        if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}
    ]
    assert prohibidos == []


def test_pantalla_de_analisis_usa_composicion_en_vez_de_repositorios():
    ruta = ROOT / "ui" / "pagina_analisis.py"
    fuente = ruta.read_text(encoding="utf-8")
    modulos = _imports(ruta)

    assert "infraestructura.composicion.prestamos_para_escenarios" in modulos
    assert all(
        not modulo.startswith("infraestructura.repositorios")
        for modulo in modulos
    )
    assert "PrestamoRepo(" not in fuente
    assert "ParticipacionRepo(" not in fuente
