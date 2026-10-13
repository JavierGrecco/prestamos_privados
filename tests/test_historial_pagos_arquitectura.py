"""Guardas de arquitectura del historial auditable de pagos."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_consulta_de_aplicacion_no_importa_sqlite_ni_infraestructura():
    archivo = ROOT / "aplicacion" / "consultas" / "historial_pagos.py"
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
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
        "El historial de aplicación debe depender del puerto público; "
        "el SQL se resuelve en infraestructura/consultas/historial_pagos.py:\\n- "
        + "\\n- ".join(problemas)
    )


def test_pantalla_pagos_usa_la_fabrica_de_historial():
    archivo = ROOT / "ui" / "pagina_pagos.py"
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    problemas: list[str] = []

    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        if isinstance(nodo.func, ast.Name) and nodo.func.id == "HistorialPagosQuery":
            problemas.append(
                f"línea {nodo.lineno}: construye HistorialPagosQuery directamente"
            )

    assert not problemas, (
        "La UI debe consumir crear_historial_pagos_query desde composición:\\n- "
        + "\\n- ".join(problemas)
    )
