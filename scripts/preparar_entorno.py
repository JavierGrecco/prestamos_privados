"""Prepara .venv e instala dependencias sin tocar SQLite.

Ejecutar desde la raíz del checkout:
    python scripts/preparar_entorno.py
    python scripts/preparar_entorno.py --runtime
"""
from __future__ import annotations
import argparse
import subprocess
import sys
import venv
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]


def error_raiz(root: Path, cwd: Path) -> str | None:
    raiz, actual = root.resolve(), cwd.resolve()
    requeridos = (raiz / "pyproject.toml", raiz / "requirements.txt",
                  raiz / "scripts" / "migrar_base.py")
    if not all(p.is_file() for p in requeridos):
        return "No se reconoce la raíz del proyecto: faltan archivos base del checkout."
    if actual != raiz:
        return f"Estás en {actual}, pero el proyecto está en {raiz}. Cambiá a la raíz del repositorio y repetí el comando."
    return None


def version_soportada(version: Sequence[int]) -> bool:
    return tuple(version[:2]) >= (3, 11)


def ruta_python_venv(root: Path, windows: bool) -> Path:
    return root / ".venv" / ("Scripts/python.exe" if windows else "bin/python")


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepara el entorno virtual declarado por este proyecto; no modifica bases de datos."
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--runtime", action="store_true",
                       help="Instala solo requirements.txt para ejecutar la aplicación.")
    grupo.add_argument("--dev", action="store_true",
                       help="Instala requirements-dev.txt con herramientas de pruebas (predeterminado).")
    return parser


def ejecutar(argv: list[str] | None = None, *, root: Path = ROOT,
             cwd: Path | None = None, version_actual: Sequence[int] | None = None,
             windows: bool | None = None, env_builder: object | None = None,
             runner: Callable = subprocess.run,
             output: Callable[[str], None] = print) -> int:
    args = construir_parser().parse_args(argv)
    root = root.resolve()
    cwd = (Path.cwd() if cwd is None else cwd).resolve()
    error = error_raiz(root, cwd)
    if error:
        output(f"ERROR: {error}")
        return 2

    version_actual = sys.version_info if version_actual is None else version_actual
    if not version_soportada(version_actual):
        output(f"ERROR: Python {version_actual[0]}.{version_actual[1]} no está soportado. Instalá Python 3.11 o posterior.")
        return 2

    windows = sys.platform == "win32" if windows is None else windows
    carpeta_venv = root / ".venv"
    python_venv = ruta_python_venv(root, windows)
    if carpeta_venv.exists() and not python_venv.is_file():
        output(
            f"ERROR: existe {carpeta_venv}, pero falta {python_venv.relative_to(root)}. "
            "No se borró ni reemplazó nada. Si el entorno proviene de otro sistema "
            "operativo, renombrá .venv manualmente y repetí la preparación."
        )
        return 2

    if not python_venv.is_file():
        try:
            (env_builder or venv.EnvBuilder(with_pip=True)).create(carpeta_venv)
        except Exception as exc:
            output(f"ERROR: no se pudo crear el entorno virtual: {type(exc).__name__}: {exc}")
            return 1
    if not python_venv.is_file():
        output(f"ERROR: no se encontró el intérprete del entorno creado: {python_venv}")
        return 1

    consulta = runner(
        [str(python_venv), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    if consulta.returncode:
        output("ERROR: no se pudo ejecutar el intérprete del entorno virtual.")
        if consulta.stderr:
            output(consulta.stderr.strip())
        return 1
    try:
        version = tuple(int(p) for p in consulta.stdout.strip().split(".")[:2])
    except ValueError:
        output("ERROR: el intérprete del entorno devolvió una versión no reconocida.")
        return 1
    if not version_soportada(version):
        output(f"ERROR: .venv usa Python {consulta.stdout.strip()}, inferior a 3.11. No se modificó el entorno existente.")
        return 2

    manifiesto = "requirements.txt" if args.runtime else "requirements-dev.txt"
    instalacion = runner([str(python_venv), "-m", "pip", "install", "-r", manifiesto],
                         cwd=root, check=False)
    if instalacion.returncode:
        output(f"ERROR: falló la instalación desde {manifiesto}. Revisá la salida anterior.")
        return instalacion.returncode or 1

    chequeo = runner([str(python_venv), "-m", "pip", "check"],
                     cwd=root, capture_output=True, text=True, check=False)
    if chequeo.returncode:
        output("ERROR: pip check detectó dependencias incompatibles.")
        if chequeo.stdout:
            output(chequeo.stdout.strip())
        if chequeo.stderr:
            output(chequeo.stderr.strip())
        return chequeo.returncode or 1

    output(f"Entorno listo: {carpeta_venv}")
    output(f"Python verificado: {version[0]}.{version[1]}")
    output(f"Dependencias instaladas desde: {manifiesto}")
    output("La base SQLite no fue creada, migrada ni modificada.")
    output("Siguiente paso: activá este .venv y seguí docs/INSTALACION_LOCAL.md.")
    return 0


def main() -> int:
    return ejecutar()


if __name__ == "__main__":
    raise SystemExit(main())
