"""Guardas para mantener los listados de personas detrás de composición."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGINA_PRINCIPAL = ROOT / "ui" / "pagina_principal.py"
PAGINA_ALTA = ROOT / "ui" / "pagina_alta_prestamo.py"


def _imports_de_repositorios(fuente: str, archivo: Path) -> list[str]:
    """Detecta imports estáticos de repositorios concretos."""
    arbol = ast.parse(fuente, filename=str(archivo))
    problemas: list[str] = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if alias.name == "infraestructura.repositorios" or alias.name.startswith(
                    "infraestructura.repositorios."
                ):
                    problemas.append(f"línea {nodo.lineno}: {alias.name}")
        elif isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ""
            if modulo == "infraestructura.repositorios" or modulo.startswith(
                "infraestructura.repositorios."
            ):
                problemas.append(f"línea {nodo.lineno}: {modulo}")

    return problemas


def test_pagina_principal_consulta_persona_por_composicion():
    fuente = PAGINA_PRINCIPAL.read_text(encoding="utf-8")

    assert _imports_de_repositorios(fuente, PAGINA_PRINCIPAL) == []
    assert (
        "from infraestructura.composicion.personas import crear_servicio_personas"
        in fuente
    )
    assert "servicio_personas.obtener(persona_id)" in fuente
    assert "except ValueError:" in fuente


def test_alta_prestamo_lista_personas_por_composicion_publica():
    fuente = PAGINA_ALTA.read_text(encoding="utf-8")

    assert _imports_de_repositorios(fuente, PAGINA_ALTA) == []
    assert (
        "from infraestructura.composicion.personas import crear_servicio_personas"
        in fuente
    )
    assert "servicio_personas.listar(rol=\"DEUDOR\")" in fuente
    assert "servicio_personas.listar(rol=\"INVERSOR\")" in fuente
