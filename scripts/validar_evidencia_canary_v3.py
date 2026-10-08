"""Valida un paquete completo de evidencia previo al canary V3.

Uso:
    python -m scripts.validar_evidencia_canary_v3 readiness.json backup.db
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from aplicacion.servicios.validador_evidencia_canary_v3 import (
    ValidadorEvidenciaCanaryV3,
)


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Valida readiness + backup antes de un canary V3."
    )
    parser.add_argument("readiness", type=Path)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--max-age-hours", type=float, default=24.0)
    parser.add_argument("--min-runs", type=int, default=100)
    parser.add_argument("--min-match", type=float, default=1.0)
    parser.add_argument("--max-divergences", type=int, default=0)
    parser.add_argument("--max-errors", type=int, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        resultado = ValidadorEvidenciaCanaryV3(
            schema_minimo=13,
            ejecuciones_minimas=args.min_runs,
            tasa_coincidencia_minima=args.min_match,
            divergencias_maximas=args.max_divergences,
            errores_maximos=args.max_errors,
            max_edad_horas=args.max_age_hours,
        ).validar(
            args.readiness,
            args.backup,
        )
        payload = {
            "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "readiness": str(args.readiness.resolve()),
            "backup": str(args.backup.resolve()),
            "apto": resultado.apto,
            "formato_ok": resultado.formato_ok,
            "readiness_ok": resultado.readiness_ok,
            "backup_ok": resultado.backup_ok,
            "antiguedad_ok": resultado.antiguedad_ok,
            "edad_segundos": resultado.edad_segundos,
            "sha256_backup": resultado.sha256_backup,
            "motivos_rechazo": list(resultado.motivos_rechazo),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if resultado.apto else 2
    except Exception as exc:
        print(
            json.dumps(
                {
                    "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
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
