"""Guardas de arquitectura para registrar aportes de reposición."""

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


def test_servicio_de_aporte_no_importa_sqlite_ni_infraestructura():
    ruta = ROOT / "aplicacion" / "servicios" / "registrar_aporte_reposicion.py"
    prohibidos = [
        modulo for modulo in _imports(ruta)
        if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}
    ]
    assert prohibidos == []


def test_puerto_de_aportes_no_depende_de_persistencia_concreta():
    ruta = ROOT / "aplicacion" / "puertos" / "registrar_aporte_reposicion.py"
    prohibidos = [
        modulo for modulo in _imports(ruta)
        if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}
    ]
    assert prohibidos == []


def test_simulador_registra_aportes_mediante_composicion_publica():
    ruta = ROOT / "ui" / "pagina_simulador_carencia.py"
    fuente = ruta.read_text(encoding="utf-8")
    modulos = _imports(ruta)

    assert "infraestructura.composicion.registrar_aporte_reposicion" in modulos
    assert "crear_servicio_registrar_aporte_reposicion(db).registrar(" in fuente
    assert "repo.registrar_aporte(" not in fuente
