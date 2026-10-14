"""Guardas arquitectónicas para el preview Legacy/V3."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _imports(archivo: Path) -> list[tuple[int, str]]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    resultado = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            resultado.extend((nodo.lineno, alias.name) for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            resultado.append((nodo.lineno, nodo.module))
    return resultado


def test_preview_legacy_depende_del_puerto_y_no_de_la_clase_concreta():
    archivo = ROOT / "aplicacion" / "consultas" / "preview_pago.py"
    imports = _imports(archivo)
    concretos = [
        f"línea {linea}: importa {modulo}"
        for linea, modulo in imports
        if modulo in {
            "aplicacion.servicios.pagos",
            "aplicacion.servicios.pagos_simulacion",
        }
    ]

    assert concretos == []
    assert any(
        modulo == "aplicacion.puertos.preview_pago"
        for _, modulo in imports
    )
    fuente = archivo.read_text(encoding="utf-8")
    assert "legacy: SimuladorPagoLegacy" in fuente


def test_puerto_preview_legacy_no_importa_servicios_ni_infraestructura():
    archivo = ROOT / "aplicacion" / "puertos" / "preview_pago.py"
    problemas = []
    for linea, modulo in _imports(archivo):
        raiz = modulo.split(".", 1)[0]
        if raiz in {"infraestructura", "sqlite3"} or modulo.startswith(
            "aplicacion.servicios"
        ):
            problemas.append(f"línea {linea}: importa {modulo}")

    assert problemas == []
    fuente = archivo.read_text(encoding="utf-8")
    assert "class SimuladorPagoLegacy(Protocol)" in fuente
