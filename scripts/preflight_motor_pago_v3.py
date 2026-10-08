"""Ejecuta el preflight V3 contra una base SQLite existente.

El comando es de solo lectura: no aplica migraciones, no registra observaciones
y no cambia el modo del motor.

Uso:
    python -m scripts.preflight_motor_pago_v3 datos/prestamos.db
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from aplicacion.servicios.preflight_motor_pago_v3 import PreflightMotorPagoV3
from infraestructura import BaseDatos


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evalúa la preparación de una base SQLite para activar V3."
    )
    parser.add_argument(
        "db",
        type=Path,
        help="Ruta de la base SQLite existente.",
    )
    parser.add_argument("--min-runs", type=int, default=100)
    parser.add_argument("--min-match", type=str, default="1")
    parser.add_argument("--max-divergences", type=int, default=0)
    parser.add_argument("--max-errors", type=int, default=0)
    parser.add_argument("--min-schema", type=int, default=12)
    return parser


def ejecutar(db_path: Path, args: argparse.Namespace) -> int:
    if not db_path.exists():
        raise FileNotFoundError(f"No existe la base: {db_path}")

    from decimal import Decimal

    with BaseDatos(db_path) as db:
        resultado = PreflightMotorPagoV3(
            db,
            version_minima=args.min_schema,
            ejecuciones_minimas=args.min_runs,
            tasa_coincidencia_minima=Decimal(args.min_match),
            divergencias_maximas=args.max_divergences,
            errores_maximos=args.max_errors,
        ).evaluar()

        payload = {
            "database": str(db_path.resolve()),
            "apto": resultado.apto,
            "criterios": [
                {
                    "nombre": criterio.nombre,
                    "cumplido": criterio.cumplido,
                    "detalle": criterio.detalle,
                }
                for criterio in resultado.criterios
            ],
            "motivos_rechazo": list(resultado.motivos_rechazo),
        }

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if resultado.apto else 2


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    try:
        return ejecutar(args.db, args)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "apto": False,
                    "error": f"{type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
