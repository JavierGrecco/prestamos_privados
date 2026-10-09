"""Verifica entorno y schema antes de iniciar Streamlit.

Exige ruta explícita de SQLite y no actualiza una base existente sin autorización
expresa y backup verificado.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]


def error_raiz(root: Path, cwd: Path) -> str | None:
    root, cwd = root.resolve(), cwd.resolve()
    requeridos = (root / "pyproject.toml", root / "scripts" / "migrar_base.py",
                  root / "ui" / "app.py")
    if not all(p.is_file() for p in requeridos):
        return "No se reconoce la raíz del proyecto: faltan archivos base del checkout."
    if cwd != root:
        return f"Estás en {cwd}, pero el proyecto está en {root}. Cambiá a la raíz del repositorio y repetí el comando."
    return None


def en_venv_del_checkout(root: Path, prefix: Path, base_prefix: Path) -> bool:
    return prefix.resolve() != base_prefix.resolve() and prefix.resolve() == (root.resolve() / ".venv").resolve()


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspecciona una base SQLite explícita y solo entonces inicia Streamlit."
    )
    parser.add_argument("--db", type=Path, required=True,
                        help="Ruta exacta de la base que se quiere utilizar.")
    parser.add_argument("--actualizar-migraciones", action="store_true",
                        help="Autoriza actualizar una base existente con migraciones pendientes.")
    parser.add_argument("--backup", type=Path,
                        help="Ruta nueva para el backup verificado obligatorio al migrar una base existente.")
    return parser


def _comando_migrador(ejecutable: str, db: Path, *, aplicar: bool = False,
                      backup: Path | None = None) -> list[str]:
    comando = [ejecutable, "-m", "scripts.migrar_base", str(db)]
    if aplicar:
        comando.append("--aplicar")
    if backup is not None:
        comando.extend(["--backup", str(backup)])
    return comando


def _leer_resultado(comando: list[str], root: Path, runner: Callable) -> tuple[int, dict | None, str]:
    resultado = runner(comando, cwd=root, capture_output=True, text=True, check=False)
    try:
        payload = json.loads(resultado.stdout.strip()) if resultado.stdout.strip() else None
    except json.JSONDecodeError:
        payload = None
    return resultado.returncode, payload, resultado.stderr.strip()


def ejecutar(argv: list[str] | None = None, *, root: Path = ROOT,
             cwd: Path | None = None, ejecutable: str | None = None,
             prefix: Path | None = None, base_prefix: Path | None = None,
             version_actual: Sequence[int] | None = None,
             runner: Callable = subprocess.run,
             output: Callable[[str], None] = print) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    root = root.resolve()
    cwd = (Path.cwd() if cwd is None else cwd).resolve()
    error = error_raiz(root, cwd)
    if error:
        output(f"ERROR: {error}")
        return 2

    version_actual = sys.version_info if version_actual is None else version_actual
    if tuple(version_actual[:2]) < (3, 11):
        output(
            f"ERROR: Python {version_actual[0]}.{version_actual[1]} no está soportado. "
            "Usá Python 3.11 o posterior y prepará el .venv de este checkout."
        )
        return 2

    ejecutable = sys.executable if ejecutable is None else ejecutable
    prefix = Path(sys.prefix if prefix is None else prefix)
    base_prefix = Path(sys.base_prefix if base_prefix is None else base_prefix)
    if not en_venv_del_checkout(root, prefix, base_prefix):
        output(
            "ERROR: no estás usando el entorno .venv de este checkout. Activá "
            "el entorno de esta carpeta antes de iniciar la aplicación. "
            f"Intérprete actual: {ejecutable}"
        )
        return 2

    if args.actualizar_migraciones and args.backup is None:
        parser.error("--actualizar-migraciones requiere --backup con una ruta nueva.")
    if args.backup is not None and not args.actualizar_migraciones:
        parser.error("--backup solo se admite junto con --actualizar-migraciones.")

    db = args.db.expanduser()
    if not db.is_absolute():
        db = root / db
    db = db.resolve()
    backup = args.backup.expanduser() if args.backup is not None else None
    if backup is not None and not backup.is_absolute():
        backup = root / backup
    if backup is not None:
        backup = backup.resolve()
        if backup == db:
            output("ERROR: la ruta del backup no puede ser la misma que la base.")
            return 2

    output(f"Base seleccionada: {db}")
    codigo, estado, detalle = _leer_resultado(_comando_migrador(ejecutable, db), root, runner)
    if estado is None:
        output("ERROR: no se pudo interpretar el resultado de inspección de la base.")
        if detalle:
            output(detalle)
        return codigo or 1

    resultado = estado.get("resultado")
    if resultado == "BASE_INEXISTENTE":
        output("Se inicializará el schema de una base nueva en la ruta indicada.")
        codigo, estado, detalle = _leer_resultado(
            _comando_migrador(ejecutable, db, aplicar=True), root, runner
        )
        if codigo != 0 or estado is None or estado.get("resultado") not in {"APLICADA", "SIN_CAMBIOS"}:
            output("ERROR: no se pudo inicializar la base nueva; no se inicia la UI.")
            if estado:
                output(json.dumps(estado, ensure_ascii=False, indent=2))
            if detalle:
                output(detalle)
            return codigo or 1
        codigo, estado, detalle = _leer_resultado(_comando_migrador(ejecutable, db), root, runner)
        if codigo != 0 or estado is None or estado.get("resultado") != "ACTUALIZADA":
            output("ERROR: la base inicializada no pasó la inspección posterior.")
            if estado:
                output(json.dumps(estado, ensure_ascii=False, indent=2))
            if detalle:
                output(detalle)
            return codigo or 1
    elif resultado == "REQUIERE_MIGRACION":
        base_nueva_vacia = estado.get("es_base_nueva") is True
        if not args.actualizar_migraciones and not base_nueva_vacia:
            output(
                "La base existente requiere migraciones. No se modificó el schema. "
                "Inspeccioná el estado y un backup, y volvé a ejecutar con "
                "--actualizar-migraciones --backup <ruta-nueva> solo después de "
                "autorizar la actualización."
            )
            output(json.dumps(estado, ensure_ascii=False, indent=2))
            return 2
        if base_nueva_vacia:
            output("El archivo existe pero está vacío, sin datos de aplicación; se inicializará el esquema.")
            comando_aplicar = _comando_migrador(ejecutable, db, aplicar=True)
        else:
            comando_aplicar = _comando_migrador(
                ejecutable, db, aplicar=True, backup=backup
            )
        codigo, estado, detalle = _leer_resultado(comando_aplicar, root, runner)
        if codigo != 0 or estado is None or estado.get("resultado") not in {"APLICADA", "SIN_CAMBIOS"}:
            output("ERROR: la migración no terminó correctamente; no se inicia la UI.")
            if estado:
                output(json.dumps(estado, ensure_ascii=False, indent=2))
            if detalle:
                output(detalle)
            return codigo or 1
        codigo, estado, detalle = _leer_resultado(_comando_migrador(ejecutable, db), root, runner)
        if codigo != 0 or estado is None or estado.get("resultado") != "ACTUALIZADA":
            output("ERROR: la base no pasó la inspección posterior a la migración.")
            if estado:
                output(json.dumps(estado, ensure_ascii=False, indent=2))
            if detalle:
                output(detalle)
            return codigo or 1
    elif resultado != "ACTUALIZADA":
        output("ERROR: el estado de la base no permite iniciar la aplicación. No se aplicaron cambios.")
        output(json.dumps(estado, ensure_ascii=False, indent=2))
        return codigo or 2

    output("Esquema verificado. Iniciando la aplicación local en http://localhost:8501.")
    entorno = os.environ.copy()
    entorno["PRESTAMOS_AUTH_MODE"] = "local"
    entorno["PRESTAMOS_DB_PATH"] = str(db)
    ui = runner([ejecutable, "-m", "streamlit", "run", "ui/app.py"],
                cwd=root, env=entorno, check=False)
    return ui.returncode


def main() -> int:
    return ejecutar()


if __name__ == "__main__":
    raise SystemExit(main())
