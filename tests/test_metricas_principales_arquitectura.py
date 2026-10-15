"""Guardas para que el cálculo principal no vuelva a conocer SQLite."""
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _modulos_importados(ruta: Path) -> list[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    modulos: list[str] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.extend(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.append(nodo.module)
    return modulos


def test_servicio_de_metricas_no_depende_de_infraestructura_ni_sqlite():
    ruta = ROOT / "aplicacion" / "servicios" / "metricas_principales.py"
    modulos = _modulos_importados(ruta)

    dependencias_prohibidas = [
        modulo
        for modulo in modulos
        if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}
    ]

    assert dependencias_prohibidas == []


def test_calculo_de_metricas_no_consulta_la_base_de_datos():
    ruta = ROOT / "aplicacion" / "consultas" / "metricas_principales.py"
    fuente = ruta.read_text(encoding="utf-8")
    modulos = _modulos_importados(ruta)

    assert all(
        modulo.split(".", maxsplit=1)[0] not in {"infraestructura", "sqlite3"}
        for modulo in modulos
    )
    assert ".consultar_uno(" not in fuente
    assert "SELECT " not in fuente


def test_fachada_de_ui_usa_composicion_y_no_repositorios_directos():
    ruta = ROOT / "ui" / "metricas.py"
    modulos = _modulos_importados(ruta)

    assert "infraestructura.composicion.metricas_principales" in modulos
    assert all(
        not modulo.startswith("infraestructura.repositorios")
        and not modulo.startswith("infraestructura.db")
        for modulo in modulos
    )
