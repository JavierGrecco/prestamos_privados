"""Audita referencias a las APIs candidatas de pagos V3/Legacy.

Uso:
    python scripts/auditar_apis_pago.py .
    python scripts/auditar_apis_pago.py . --json

La herramienta es de solo lectura y usa AST para detectar imports sin ejecutar
el código de la aplicación.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from dataclasses import dataclass


CANDIDATAS = {
    "legacy": (
        "aplicacion.servicios.pagos.ServicioPagos",
    ),
    "v3_registro": (
        "aplicacion.servicios.registro_pago_v3.RegistrarPagoV3",
        "aplicacion.servicios.registro_pago_v3_devengamientos.RegistrarPagoV3ConDevengamientos",
        "aplicacion.servicios.registro_pago_v3_completo.RegistrarPagoV3Completo",
        "aplicacion.servicios.registro_pago_v3_completo_adelantos.RegistrarPagoV3CompletoConAdelantos",
    ),
    "v3_factory": (
        "aplicacion.servicios.fabrica_registro_pago_v3",
    ),
    "bridge": (
        "aplicacion.servicios.puente_motor_pago_v3.PuenteMotorPagoV3",
    ),
    "shadow": (
        "aplicacion.servicios.ejecutor_sombra_pago_v3.EjecutorSombraPagoV3",
        "aplicacion.servicios.sombra_pago_v3_sqlite.SombraPagoV3SQLite",
    ),
    "plan_pago_duplicado": (
        "dominio.plan_pago.PlanPago",
        "dominio.motor_pagos_v3.PlanPago",
    ),
}


@dataclass(frozen=True)
class Referencia:
    categoria: str
    simbolo: str
    archivo: str
    linea: int
    forma: str


def _iter_python_files(root: Path):
    excluded = {".git", ".venv", "venv", "__pycache__", "node_modules"}
    for path in root.rglob("*.py"):
        if any(part in excluded or part.startswith("quarantine_") for part in path.parts):
            continue
        yield path


def _candidatas_por_modulo():
    result = {}
    for categoria, simbolos in CANDIDATAS.items():
        for simbolo in simbolos:
            if "." not in simbolo:
                result.setdefault(simbolo, []).append((categoria, simbolo))
                continue
            modulo, nombre = simbolo.rsplit(".", 1)
            result.setdefault(modulo, []).append((categoria, simbolo))
    return result


def analizar(root: Path) -> tuple[Referencia, ...]:
    por_modulo = _candidatas_por_modulo()
    encontrados = []

    for path in sorted(_iter_python_files(root)):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue

        rel = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                modulo = node.module or ""
                if node.level:
                    continue
                for alias in node.names:
                    for categoria, simbolo in por_modulo.get(modulo, ()):
                        esperado = simbolo.rsplit(".", 1)[-1]
                        if alias.name == esperado or alias.name == "*":
                            encontrados.append(
                                Referencia(categoria, simbolo, rel, node.lineno, "from")
                            )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    modulo = alias.name
                    for candidato, refs in por_modulo.items():
                        if modulo == candidato or modulo.startswith(candidato + "."):
                            for categoria, simbolo in refs:
                                encontrados.append(
                                    Referencia(
                                        categoria, simbolo, rel, node.lineno, "import"
                                    )
                                )

    return tuple(encontrados)


def agrupar(referencias: tuple[Referencia, ...]):
    agrupado = {categoria: [] for categoria in CANDIDATAS}
    for ref in referencias:
        agrupado[ref.categoria].append(ref)
    return {
        categoria: [
            {
                "simbolo": ref.simbolo,
                "archivo": ref.archivo,
                "linea": ref.linea,
                "forma": ref.forma,
            }
            for ref in refs
        ]
        for categoria, refs in agrupado.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    resultado = agrupar(analizar(root))

    if args.as_json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print("=== AUDITORÍA DE APIs DE PAGOS ===")
    for categoria, refs in resultado.items():
        print(f"\n[{categoria}]")
        if not refs:
            print("  sin referencias")
            continue
        for ref in refs:
            print(
                f"  {ref['simbolo']} <- "
                f"{ref['archivo']}:{ref['linea']} ({ref['forma']})"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
