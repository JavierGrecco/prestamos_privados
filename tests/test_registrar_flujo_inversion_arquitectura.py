"""Guardas arquitectónicas para registrar flujos de inversión."""

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


def test_servicio_de_flujo_no_importa_sqlite_ni_infraestructura():
    ruta = ROOT / "aplicacion" / "servicios" / "registrar_flujo_inversion.py"
    prohibidos = [
        modulo for modulo in _imports(ruta)
        if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}
    ]
    assert prohibidos == []


def test_puerto_de_flujo_no_depende_de_persistencia_concreta():
    ruta = ROOT / "aplicacion" / "puertos" / "registrar_flujo_inversion.py"
    prohibidos = [
        modulo for modulo in _imports(ruta)
        if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}
    ]
    assert prohibidos == []


def test_simulador_registra_flujos_mediante_la_fabrica_publica():
    ruta = ROOT / "ui" / "pagina_simulador_carencia.py"
    fuente = ruta.read_text(encoding="utf-8")
    modulos = _imports(ruta)

    assert "infraestructura.composicion.registrar_flujo_inversion" in modulos
    assert "crear_servicio_registrar_flujo_inversion(db).registrar(" in fuente
    assert "repo.registrar_flujo_inversion(" not in fuente
