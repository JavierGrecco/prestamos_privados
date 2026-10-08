"""Genera un paquete de evidencia para revisión humana de canary V3.

No activa V3, no cambia configuración y no registra pagos.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from decimal import Decimal
from pathlib import Path

from aplicacion.servicios.paquete_canary_v3 import ServicioPaqueteCanaryV3
from infraestructura import BaseDatos


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Valida base + backup + readiness para revisión humana de canary."
    )
    parser.add_argument("db", type=Path, help="Base SQLite a evaluar.")
    parser.add_argument("backup", type=Path, help="Backup verificable de referencia.")
    parser.add_argument(
        "--operador",
        default=os.environ.get("PRESTAMOS_OPERADOR", ""),
        help="Operador declarado que realizará la revisión.",
    )
    parser.add_argument(
        "--motivo",
        required=True,
        help="Motivo de la revisión del canary.",
    )
    parser.add_argument("--min-runs", type=int, default=100)
    parser.add_argument("--min-match", type=str, default="1")
    parser.add_argument("--max-divergences", type=int, default=0)
    parser.add_argument("--max-errors", type=int, default=0)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force-output", action="store_true")
    return parser


def ejecutar(args: argparse.Namespace) -> int:
    if not args.db.is_file():
        raise FileNotFoundError(f"No existe la base: {args.db}")
    if not args.backup.is_file():
        raise FileNotFoundError(f"No existe el backup: {args.backup}")

    with BaseDatos(args.db) as db:
        paquete = ServicioPaqueteCanaryV3(db).evaluar(
            base_path=args.db,
            backup_path=args.backup,
            operador=args.operador,
            motivo_revision=args.motivo,
            ejecuciones_minimas=args.min_runs,
            tasa_coincidencia_minima=Decimal(args.min_match),
            divergencias_maximas=args.max_divergences,
            errores_maximos=args.max_errors,
        )

    texto = json.dumps(
        paquete.a_dict(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "
"

    if args.output:
        guardar(args.output.expanduser(), texto, force=args.force_output)

    print(texto, end="")
    return 0 if paquete.apto_para_revision_humana else 2


def guardar(destino: Path, texto: str, *, force: bool) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and not force:
        raise FileExistsError(
            f"Ya existe el paquete: {destino}. Use --force-output si el reemplazo es intencional."
        )

    temporal = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destino.parent,
            prefix=f".{destino.name}.",
            suffix=".tmp",
            delete=False,
        ) as archivo:
            temporal = Path(archivo.name)
            archivo.write(texto)
            archivo.flush()
            os.fsync(archivo.fileno())
        temporal.replace(destino)
    finally:
        if temporal is not None:
            try:
                temporal.unlink()
            except FileNotFoundError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    try:
        return ejecutar(args)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "apto_para_revision_humana": False,
                    "error": f"{type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
