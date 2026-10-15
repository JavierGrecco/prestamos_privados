"""Guardas de arquitectura de la ficha básica del préstamo."""
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


def test_consulta_de_aplicacion_no_importa_infraestructura_ni_sqlite():
    ruta = ROOT / "aplicacion" / "consultas" / "ficha_prestamo.py"
    prohibidos = [
        modulo
        for modulo in _imports(ruta)
        if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}
    ]
    assert prohibidos == []


def test_pantalla_de_prestamos_usa_fabrica_y_no_importa_repositorios():
    ruta = ROOT / "ui" / "pagina_prestamos.py"
    fuente = ruta.read_text(encoding="utf-8")
    modulos = _imports(ruta)

    assert "infraestructura.composicion.ficha_prestamo" in modulos
    assert all(
        not modulo.startswith("infraestructura.repositorios")
        for modulo in modulos
    )
    assert "crear_consulta_ficha_prestamo(db).obtener(prestamo_id)" in fuente
    assert "PrestamoRepo" not in fuente
    assert "PagoRepo" not in fuente
    assert "db.consultar_uno(" not in fuente
