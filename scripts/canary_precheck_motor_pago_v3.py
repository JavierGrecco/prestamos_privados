"""Precheck operativo previo a un canary V3.

Combina estado de integridad, preflight, modo persistido y evidencia SOMBRA.
Es de solo lectura y no cambia el modo del motor.

Uso:
    python -m scripts.canary_precheck_motor_pago_v3 datos/prestamos.db
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from aplicacion.servicios.precheck_canary_motor_pago_v3 import ServicioReadinessCanaryV3
from infraestructura import BaseDatos


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evalúa si una base está lista para un canary V3."
    )
    parser.add_argument("db", type=Path, help="Ruta de la base SQLite existente.")
    parser.add_argument("--min-runs", type=int, default=100)
    parser.add_argument("--min-match", type=str, default="1")
    parser.add_argument("--max-divergences", type=int, default=0)
    parser.add_argument("--max-errors", type=int, default=0)
    parser.add_argument("--output", type=Path, help="Guarda el informe JSON en esta ruta.")
    parser.add_argument(
        "--force-output",
        action="store_true",
        help="Permite reemplazar un artefacto existente de forma explícita.",
    )
    return parser


def ejecutar(db_path: Path, args: argparse.Namespace) -> int:
    evaluado_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not db_path.exists():
        raise FileNotFoundError(f"No existe la base: {db_path}")

    from decimal import Decimal

    with BaseDatos(db_path) as db:
        resultado = ServicioReadinessCanaryV3(
            db,
            ejecuciones_minimas=args.min_runs,
            tasa_coincidencia_minima=Decimal(args.min_match),
            divergencias_maximas=args.max_divergences,
            errores_maximos=args.max_errors,
        ).evaluar()

        payload = {
            "database": str(db_path.resolve()),
            "evaluated_at": evaluado_en,
            "listo_para_canary": resultado.listo,
            "modo_actual": resultado.modo_actual,
            "revision_modo": resultado.revision_modo,
            "integridad_ok": resultado.integridad_ok,
            "preflight_apto": resultado.preflight_apto,
            "evidencia_sombra": {
                "ejecuciones": resultado.ejecuciones_sombra,
                "coincidencia": resultado.tasa_coincidencia,
                "divergencias": resultado.divergencias,
                "errores": resultado.errores,
            },
            "motivos_rechazo": list(resultado.motivos_rechazo),
        }

    texto = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    print(texto, end="")

    if args.output is not None:
        destino = args.output.expanduser()
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.exists() and not args.force_output:
            raise FileExistsError(
                f"Ya existe el artefacto de evidencia: {destino}. "
                "Use --force-output solo cuando la sobrescritura sea intencional."
            )
        temporal = destino.with_name(destino.name + ".tmp")
        temporal.write_text(texto, encoding="utf-8")
        temporal.replace(destino)

    return 0 if resultado.listo else 2


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    try:
        return ejecutar(args.db, args)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "database": str(args.db.resolve()),
                    "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "listo_para_canary": False,
                    "error": f"{type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
