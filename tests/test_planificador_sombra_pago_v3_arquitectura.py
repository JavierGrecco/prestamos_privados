"""Guardas arquitectónicas del planificador SOMBRA de pagos V3."""

import ast
from pathlib import Path

from aplicacion.servicios.planificador_sombra_pago_v3 import PlanificadorSombraPagoV3
from aplicacion.servicios.sombra_pago_v3_sqlite import SombraPagoV3SQLite


ROOT = Path(__file__).resolve().parents[1]
PLANNER = ROOT / "aplicacion" / "servicios" / "planificador_sombra_pago_v3.py"
SHIM = ROOT / "aplicacion" / "servicios" / "sombra_pago_v3_sqlite.py"
COMPOSITION = ROOT / "infraestructura" / "composicion" / "registradores_pago.py"


def test_planificador_sombra_no_importa_sqlite_ni_infraestructura():
    fuente = PLANNER.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(PLANNER))
    problemas: list[str] = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module] if nodo.module else []
        else:
            continue

        for modulo in modulos:
            if modulo.split(".", maxsplit=1)[0] in {"infraestructura", "sqlite3"}:
                problemas.append(f"línea {nodo.lineno}: importa {modulo}")

    assert not problemas, (
        "El planificador SOMBRA debe depender del puerto de lectura, no de SQLite:\\n- "
        + "\\n- ".join(problemas)
    )
    assert "ConsultaEstadoPagoSombraV3" in fuente
    assert "EstadoRegistroPagoV3" in fuente


def test_nombre_historico_es_un_alias_y_no_duplica_logica():
    fuente = SHIM.read_text(encoding="utf-8")
    assert "SombraPagoV3SQLite = PlanificadorSombraPagoV3" in fuente
    assert "import sqlite3" not in fuente
    assert "from infraestructura" not in fuente
    assert SombraPagoV3SQLite is PlanificadorSombraPagoV3


def test_composicion_sombra_usa_el_planificador_neutral():
    fuente = COMPOSITION.read_text(encoding="utf-8")
    assert "from aplicacion.servicios.planificador_sombra_pago_v3 import" in fuente
    assert "PlanificadorSombraPagoV3(" in fuente
    assert "from aplicacion.servicios.sombra_pago_v3_sqlite import" not in fuente
    assert "SombraPagoV3SQLite(" not in fuente
