"""Inventario reproducible de dependencias entre capas del repositorio.

Usa AST sin importar ni ejecutar módulos de la aplicación. Es un diagnóstico:
distingue reglas pendientes, excepciones temporales y composición de borde; no
falla solo porque el código todavía tenga deuda técnica.

Uso:
    python scripts/auditar_fronteras_modulares.py .
    python scripts/auditar_fronteras_modulares.py . --format markdown
    python scripts/auditar_fronteras_modulares.py . --format json
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


CAPAS = {"dominio", "aplicacion", "infraestructura", "ui", "scripts"}
EXCLUIR = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"}
ORDEN_SEVERIDAD = {"ALTA": 0, "MEDIA": 1, "BAJA": 2, "INFO": 3}

# Transiciones conocidas: se reportan, no se esconden del inventario.
EXCEPCIONES_TEMPORALES = {
    "aplicacion/servicios/pagos.py": (
        "#270",
        "La fachada de pagos conserva compatibilidad con consumidores históricos.",
        "Trasladar la composición restante a infraestructura/composicion y revisar consumidores externos antes de retirar el puente.",
    ),
    "aplicacion/servicios/registro_pago_ui.py": (
        "#270",
        "La composición del registrador de UI conserva una transición pendiente.",
        "Inyectar el caso de uso y las consultas por contratos; ensamblar adaptadores en infraestructura/composicion.",
    ),
    "aplicacion/servicios/fabrica_registro_pago_v3.py": (
        "#270",
        "Fábrica temporal V3 ubicada en aplicación, pendiente de consolidar en composición.",
        "Mover el ensamblado concreto a infraestructura/composicion y migrar consumidores.",
    ),
    "aplicacion/servicios/sombra_pago_v3_sqlite.py": (
        "#270",
        "Adaptador SOMBRA con SQLite conserva una ubicación histórica de aplicación.",
        "Separar adaptador concreto del caso de uso y mantener compatibilidad solo mientras existan consumidores.",
    ),
    "aplicacion/servicios/fabrica_sombra_pago_v3_sqlite.py": (
        "#270",
        "Fábrica de SOMBRA específica de SQLite pendiente de quedar en composición.",
        "Mover la composición y validar que Legacy siga siendo el resultado efectivo.",
    ),
    "aplicacion/servicios/prestamos.py": (
        "#301",
        "El alta completa del préstamo debe conservar una única transacción durante la migración.",
        "Completar puertos y unidad de trabajo sin separar préstamo, cuotas, participaciones, ledger y auditoría.",
    ),
    "aplicacion/servicios/personas.py": (
        "#267",
        "La migración de límites de personas requiere confirmar todos los consumidores restantes.",
        "Revisar imports restantes y mantener personas/roles detrás de la API pública.",
    ),
}

SQL_INICIO = re.compile(
    r"(?is)^\s*(?:SELECT\b.*?\bFROM\b|INSERT\s+INTO\b|"
    r"UPDATE\s+[\w.]+\s+SET\b|DELETE\s+FROM\b|PRAGMA\s+[\w.]+|"
    r"ALTER\s+TABLE\b|CREATE\s+TABLE\b|DROP\s+TABLE\b)"
)


@dataclass(frozen=True, order=True)
class Hallazgo:
    severidad: str
    codigo: str
    estado: str
    capa: str
    archivo: str
    linea: int
    dependencia: str
    motivo: str
    riesgo: str
    siguiente_paso: str
    issue: str = ""


@dataclass(frozen=True)
class Inventario:
    archivos_python: int
    archivos_analizados: int
    errores_analisis: tuple[dict, ...]
    importaciones: int
    importaciones_entre_capas: int
    dependencias_entre_capas: tuple[dict, ...]
    archivos_por_capa: dict[str, int]
    hallazgos: tuple[Hallazgo, ...]


def _iter_python_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if not rel.parts or rel.parts[0] not in CAPAS:
            continue
        if any(part in EXCLUIR or part.startswith("quarantine_") for part in rel.parts):
            continue
        yield path


def _layer(path: Path, root: Path) -> str:
    return path.relative_to(root).parts[0]


def _package_parts(path: Path, root: Path) -> tuple[str, ...]:
    parts = path.relative_to(root).with_suffix("").parts
    return parts if parts and parts[-1] == "__init__" else parts[:-1]


def _resolve_import_module(path: Path, root: Path, node: ast.ImportFrom) -> str:
    if not node.level:
        return node.module or ""
    package = _package_parts(path, root)
    up = node.level - 1
    if up:
        package = package[: max(0, len(package) - up)]
    suffix = tuple((node.module or "").split(".")) if node.module else ()
    return ".".join((*package, *suffix)).strip(".")


def _target_layer(module: str) -> str | None:
    root_name = module.split(".", 1)[0] if module else ""
    return root_name if root_name in CAPAS else None


def _parse_file(path: Path, root: Path):
    rel = path.relative_to(root).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        return None, [], f"{type(exc).__name__}: {exc}"

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno, (alias.asname or alias.name,)))
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_import_module(path, root, node)
            imports.append((module, node.lineno, tuple(alias.name for alias in node.names)))
    return tree, imports, None


def _hallazgo_import(rel, capa, linea, modulo, nombres, destino):
    dependencia = modulo or "(import relativo no resuelto)"
    if nombres:
        dependencia += " [" + ", ".join(nombres) + "]"
    transicion = EXCEPCIONES_TEMPORALES.get(rel)

    if capa == "dominio" and destino in {"aplicacion", "infraestructura", "ui"}:
        return Hallazgo("ALTA", "DOM-DEPENDENCIA-ASCENDENTE", "PENDIENTE", capa, rel, linea, dependencia,
            "El dominio contiene reglas y tipos de negocio, y no debe depender de capas externas.",
            "Puede crear acoplamiento, ciclos de importación y pruebas difíciles de aislar.",
            "Mover el contrato o la regla al dominio e invertir la dependencia mediante tipos/puertos.", "#267")
    if capa == "aplicacion" and destino == "ui":
        return Hallazgo("ALTA", "APP-IMPORTA-UI", "PENDIENTE", capa, rel, linea, dependencia,
            "La aplicación no debe depender de una pantalla o de Streamlit.",
            "Acopla casos de uso con la presentación y puede formar ciclos.",
            "Mover el contrato compartido a aplicación o dominio y dejar la UI como consumidora.", "#267")
    if capa == "infraestructura" and destino == "ui":
        return Hallazgo("ALTA", "INFRA-IMPORTA-UI", "PENDIENTE", capa, rel, linea, dependencia,
            "La infraestructura no debe conocer la capa de presentación.",
            "Acopla persistencia a la UI y dificulta reutilizar adaptadores desde otras entradas.",
            "Mover el contrato a aplicación y mantener composición en infraestructura.", "#267")
    if capa == "aplicacion" and destino == "infraestructura":
        db = modulo.startswith("infraestructura.db") or "BaseDatos" in nombres
        repo = modulo.startswith("infraestructura.repositorios")
        compose = modulo.startswith("infraestructura.composicion")
        if db or repo:
            code, severity = "APP-IMPORTA-DB-REPO", "ALTA"
            motivo = "El caso de uso conoce una conexión o un repositorio concreto en lugar de un contrato."
            risk = "Dificulta pruebas sin SQLite, sustitución de adaptadores y conservación explícita de la unidad de trabajo."
            next_step = "Definir e inyectar un puerto de aplicación y ensamblar el adaptador en infraestructura/composicion."
            issue = "#301" if rel.startswith("aplicacion/servicios/prestamos") else "#270"
        elif compose:
            code, severity = "APP-IMPORTA-COMPOSICION", "MEDIA"
            motivo = "La composición concreta debe vivir en el borde de infraestructura, no dentro del caso de uso."
            risk = "El caso de uso decide cómo construir adaptadores y cuesta probarlo con sustitutos simples."
            next_step = "Inyectar la dependencia y construirla en infraestructura/composicion."
            issue = "#270"
        else:
            code, severity = "APP-IMPORTA-INFRA", "MEDIA"
            motivo = "Dependencia desde aplicación a infraestructura pendiente de caracterización."
            risk = "Reduce la capacidad de sustituir persistencia y puede ocultar una frontera incompleta."
            next_step = "Revisar si corresponde a un puerto mal ubicado, un adaptador temporal o una dependencia por migrar."
            issue = "#293"
        state = "EXCEPCION_TEMPORAL_DOCUMENTADA" if transicion else "PENDIENTE_DE_REVISION"
        if transicion:
            issue, rationale, next_step = transicion
            motivo = motivo + " Transición documentada: " + rationale
        return Hallazgo(severity, code, state, capa, rel, linea, dependencia, motivo, risk, next_step, issue)
    if capa == "ui" and destino == "infraestructura":
        if modulo.startswith("infraestructura.composicion"):
            return Hallazgo("INFO", "UI-USA-COMPOSICION", "BORDE_DE_COMPOSICION", capa, rel, linea, dependencia,
                "La UI puede invocar una fábrica pública en el borde; la fábrica debe ensamblar los repositorios.",
                "Revisar que la pantalla no exponga SQL, transacciones ni reglas financieras.",
                "Mantener llamadas a fábricas/casos de uso públicos; no instanciar repositorios desde la UI.", "#267")
        repo = modulo.startswith("infraestructura.repositorios")
        db = modulo.startswith("infraestructura.db") or "BaseDatos" in nombres
        return Hallazgo("ALTA" if repo or db else "MEDIA",
            "UI-ACCESO-INFRA-DIRECTO" if repo or db else "UI-IMPORTA-INFRA",
            "PENDIENTE_DE_MIGRACION", capa, rel, linea, dependencia,
            "La pantalla debe capturar la intención del usuario y consumir consultas/casos de uso públicos.",
            "Puede duplicar composición, exponer detalles de persistencia y complicar las pruebas de UI.",
            "Mover la construcción a la fábrica de composición e inyectar un contrato estable.",
            "#302" if repo else "#267")
    return None


def analizar(root: Path) -> Inventario:
    """Analiza todos los archivos Python de las capas acordadas."""
    root = root.resolve()
    archivos = tuple(_iter_python_files(root))
    por_capa = Counter(_layer(path, root) for path in archivos)
    errores: list[dict] = []
    hallazgos: list[Hallazgo] = []
    edges: Counter[tuple[str, str]] = Counter()
    total_imports = 0
    total_edges = 0

    for path in archivos:
        rel = path.relative_to(root).as_posix()
        capa = _layer(path, root)
        tree, imports, error = _parse_file(path, root)
        if error:
            errores.append({"archivo": rel, "error": error})
            continue
        total_imports += len(imports)
        for module, line, names in imports:
            target = _target_layer(module)
            if target and target != capa:
                total_edges += 1
                edges[(capa, target)] += 1
                finding = _hallazgo_import(rel, capa, line, module, names, target)
                if finding:
                    hallazgos.append(finding)
        if tree is None or capa not in {"aplicacion", "ui"}:
            continue

        repositories_imported: set[str] = set()
        databases_imported: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            module = _resolve_import_module(path, root, node)
            if module.startswith("infraestructura.repositorios"):
                for alias in node.names:
                    if alias.name.endswith("Repo") or alias.name.endswith("Repository"):
                        repositories_imported.add(alias.asname or alias.name)
            if module.startswith("infraestructura.db"):
                for alias in node.names:
                    if alias.name == "BaseDatos":
                        databases_imported.add(alias.asname or alias.name)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = func.id if isinstance(func, ast.Name) else (
                    func.attr if isinstance(func, ast.Attribute) else ""
                )
                if name == "BaseDatos" or name in databases_imported:
                    hallazgos.append(Hallazgo("ALTA", "CONSTRUYE-BASE-DATOS", "PENDIENTE_DE_MIGRACION",
                        capa, rel, node.lineno, name + "(...)",
                        "Aplicación/UI no debe abrir conexiones concretas a SQLite.",
                        "Puede crear conexiones fuera de la unidad de trabajo o de la fábrica oficial.",
                        "Inyectar la conexión o el puerto desde composición y preservar una sola unidad transaccional.",
                        "#270" if capa == "aplicacion" else "#302"))
                elif name.endswith("Repo") or name.endswith("Repository") or name in repositories_imported:
                    hallazgos.append(Hallazgo("ALTA", "CONSTRUYE-REPOSITORIO", "PENDIENTE_DE_MIGRACION",
                        capa, rel, node.lineno, name + "(...)",
                        "La construcción de un repositorio concreto pertenece a infraestructura/composicion.",
                        "La pantalla o caso de uso queda acoplado a SQLite y puede saltarse contratos o atomicidad.",
                        "Mover la construcción a composición e inyectar el contrato.",
                        "#301" if capa == "aplicacion" and "prestamos" in rel else ("#302" if capa == "ui" else "#270")))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and SQL_INICIO.search(node.value):
                first_line = node.value.strip().splitlines()[0][:100]
                hallazgos.append(Hallazgo("ALTA", "SQL-EN-CAPA-EXTERNA", "PENDIENTE_DE_MIGRACION",
                    capa, rel, getattr(node, "lineno", 1), first_line,
                    "El SQL debe residir en infraestructura, detrás de un puerto.",
                    "Puede saltarse operaciones de repositorio y dificulta probar la lógica sin base real.",
                    "Mover SQL al adaptador de infraestructura y exponer una operación tipada.",
                    "#270" if capa == "aplicacion" else "#267"))

    unique = {}
    for h in hallazgos:
        key = (h.severidad, h.codigo, h.estado, h.capa, h.archivo, h.linea,
               h.dependencia, h.motivo, h.riesgo, h.siguiente_paso, h.issue)
        unique[key] = h
    ordered = tuple(sorted(unique.values(), key=lambda h: (
        ORDEN_SEVERIDAD.get(h.severidad, 9), h.codigo, h.archivo, h.linea, h.dependencia
    )))
    return Inventario(
        len(archivos), len(archivos) - len(errores),
        tuple(sorted(errores, key=lambda x: x["archivo"])),
        total_imports, total_edges,
        tuple({"origen": a, "destino": b, "importaciones": count}
              for (a, b), count in sorted(edges.items())),
        dict(sorted(por_capa.items())), ordered,
    )


def _summary(inv: Inventario) -> dict:
    severity = Counter(h.severidad for h in inv.hallazgos)
    states = Counter(h.estado for h in inv.hallazgos)
    rules = Counter(h.codigo for h in inv.hallazgos)
    return {
        "archivos_python": inv.archivos_python,
        "archivos_analizados": inv.archivos_analizados,
        "errores_analisis": len(inv.errores_analisis),
        "importaciones": inv.importaciones,
        "importaciones_entre_capas": inv.importaciones_entre_capas,
        "hallazgos": len(inv.hallazgos),
        "por_severidad": dict(sorted(severity.items())),
        "por_estado": dict(sorted(states.items())),
        "por_regla": dict(sorted(rules.items())),
        "archivos_por_capa": inv.archivos_por_capa,
        "dependencias_entre_capas": inv.dependencias_entre_capas,
    }


def _limit(items: tuple[Hallazgo, ...], maximum: int) -> tuple[Hallazgo, ...]:
    return items if maximum <= 0 else items[:maximum]


def a_json(inv: Inventario) -> str:
    return json.dumps({
        "resumen": _summary(inv),
        "errores_analisis": inv.errores_analisis,
        "hallazgos": [asdict(h) for h in inv.hallazgos],
    }, ensure_ascii=False, indent=2, sort_keys=True)


def a_markdown(inv: Inventario, max_hallazgos: int = 0) -> str:
    summary = _summary(inv)
    lines = [
        "# Inventario automático de fronteras modulares", "",
        "> Informe generado por scripts/auditar_fronteras_modulares.py. Diagnostica el código; no equivale a aceptación funcional.", "",
        "## Resumen", "",
        f"- Archivos Python: **{summary['archivos_python']}**; analizados: **{summary['archivos_analizados']}**; errores de análisis: **{summary['errores_analisis']}**.",
        f"- Importaciones detectadas: **{summary['importaciones']}**; cruces entre capas: **{summary['importaciones_entre_capas']}**.",
        f"- Hallazgos: **{summary['hallazgos']}**.", "",
        "| Capa | Archivos Python |", "|---|---:|",
    ]
    lines.extend(f"| {layer} | {count} |" for layer, count in summary["archivos_por_capa"].items())
    lines.extend(["", "### Hallazgos por severidad", "", "| Severidad | Cantidad |", "|---|---:|"])
    lines.extend(f"| {level} | {count} |" for level, count in summary["por_severidad"].items())
    lines.extend(["", "### Dependencias entre capas", "", "| Origen | Destino | Importaciones |", "|---|---|---:|"])
    lines.extend(f"| {e['origen']} | {e['destino']} | {e['importaciones']} |" for e in inv.dependencias_entre_capas)
    lines.extend(["", "## Hallazgos y siguiente paso", "",
        "| Prioridad | Estado | Regla | Archivo:línea | Dependencia | Riesgo | Próximo paso / seguimiento |",
        "|---|---|---|---|---|---|---|"])
    findings = _limit(inv.hallazgos, max_hallazgos)
    clean = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    for h in findings:
        lines.append(f"| {h.severidad} | {clean(h.estado)} | {h.codigo} | "
            f"{h.archivo}:{h.linea} | {clean(h.dependencia)} | {clean(h.riesgo)} | "
            f"{clean(h.siguiente_paso)} ({clean(h.issue)}) |")
    omitted = len(inv.hallazgos) - len(findings)
    if omitted:
        lines.extend(["", f"_Se muestran {len(findings)} de {len(inv.hallazgos)} hallazgos; use --max-hallazgos 0 para mostrar todos._"])
    if inv.errores_analisis:
        lines.extend(["", "## Archivos que no se pudieron analizar", ""])
        lines.extend(f"- {x['archivo']}: {x['error']}" for x in inv.errores_analisis)
    return "\n".join(lines) + "\n"


def a_texto(inv: Inventario, max_hallazgos: int = 30) -> str:
    summary = _summary(inv)
    lines = [
        "=== INVENTARIO DE FRONTERAS MODULARES ===",
        f"Archivos Python: {summary['archivos_python']} (analizados: {summary['archivos_analizados']}; errores: {summary['errores_analisis']})",
        f"Importaciones: {summary['importaciones']} (entre capas: {summary['importaciones_entre_capas']})",
        f"Hallazgos: {summary['hallazgos']} | severidad: {summary['por_severidad']} | estado: {summary['por_estado']}",
        "Archivos por capa: " + ", ".join(f"{k}={v}" for k, v in summary["archivos_por_capa"].items()), "",
    ]
    findings = _limit(inv.hallazgos, max_hallazgos)
    for h in findings:
        lines.append(f"[{h.severidad}] {h.codigo} ({h.estado}) {h.archivo}:{h.linea} -> "
            f"{h.dependencia} | siguiente: {h.siguiente_paso} [{h.issue}]")
    omitted = len(inv.hallazgos) - len(findings)
    if omitted:
        lines.append(f"... {omitted} hallazgos adicionales. Use --format markdown o --format json para el detalle completo.")
    if inv.errores_analisis:
        lines.append(f"ERROR: {len(inv.errores_analisis)} archivos no se pudieron analizar.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Raíz del repositorio")
    parser.add_argument("--format", choices=("text", "markdown", "json"), default="text")
    parser.add_argument("--max-hallazgos", type=int, default=30, help="Máximo a mostrar; 0 muestra todos")
    parser.add_argument("--fail-on-parse-error", action="store_true", help="Falla si algún archivo no se puede analizar")
    args = parser.parse_args(argv)

    inventory = analizar(Path(args.root))
    if args.format == "json":
        print(a_json(inventory))
    elif args.format == "markdown":
        print(a_markdown(inventory, max_hallazgos=args.max_hallazgos), end="")
    else:
        print(a_texto(inventory, max_hallazgos=args.max_hallazgos))
    return 1 if args.fail_on_parse_error and inventory.errores_analisis else 0


if __name__ == "__main__":
    raise SystemExit(main())
