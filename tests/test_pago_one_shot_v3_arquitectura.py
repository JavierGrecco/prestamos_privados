"""Guardas de arquitectura para la proyección One Shot de pagos V3."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aplicacion" / "consultas" / "pago_one_shot_v3.py"


def test_one_shot_no_importa_infraestructura_ni_sqlite():
    """La proyección conoce el contrato público, no el adaptador que lee pagos."""
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
        "One Shot debe depender de ConsultaPagoV3Auditable en aplicación/puertos, "
        "no de infraestructura:\\n- " + "\\n- ".join(problemas)
    )
    assert "obtener_pago_v3(db" not in fuente
    assert "PagoV3Read" in fuente
    assert "ConsultaPagoV3Auditable" in fuente
