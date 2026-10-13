"""Guardas de arquitectura para planificación financiera personal."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aplicacion" / "consultas" / "planificacion_financiera_persona.py"


def test_planificacion_no_importa_sqlite_ni_repositorios_concretos():
    """La consulta coordina contratos; la composición conoce SQLite."""
    fuente = TARGET.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(TARGET))
    problemas: list[str] = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue

        for modulo in modulos:
            raiz = modulo.split(".", maxsplit=1)[0]
            if raiz in {"infraestructura", "sqlite3"}:
                problemas.append(f"línea {nodo.lineno}: importa {modulo}")

    assert not problemas, (
        "Planificación debe depender de contratos de aplicación, no de "
        "infraestructura:\n- " + "\n- ".join(problemas)
    )
    assert "BaseDatos" not in fuente
    assert "PersonaRepo" not in fuente
    assert ".consultar(" not in fuente
