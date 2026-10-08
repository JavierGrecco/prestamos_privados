"""Precheck operativo previo a un canary V3.

Combina estado de integridad, preflight, modo persistido y evidencia SOMBRA.
Es de solo lectura y no cambia el modo del motor.

Uso:
    python -m scripts.canary_precheck_motor_pago_v3 datos/prestamos.db
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from aplicacion.servicios.configuracion_motor_pago import ServicioConfiguracionMotorPago
from aplicacion.servicios.metricas_sombra_v3 import ServicioMetricasSombraV3
from aplicacion.servicios.preflight_motor_pago_v3 import PreflightMotorPagoV3
from infraestructura import BaseDatos
from infraestructura.consultas.integridad_v3 import auditar_integridad_v3


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evalúa si una base está lista para un canary V3."
    )
    parser.add_argument("db", type=Path, help="Ruta de la base SQLite existente.")
    parser.add_argument("--min-runs", type=int, default=100)
    parser.add_argument("--min-match", type=str, default="1")
    parser.add_argument("--max-divergences", type=int, default=0)
    parser.add_argument("--max-errors", type=int, default=0)
    return parser


def ejecutar(db_path: Path, args: argparse.Namespace) -> int:
    if not db_path.exists():
        raise FileNotFoundError(f"No existe la base: {db_path}")

    from decimal import Decimal

    with BaseDatos(db_path) as db:
        integridad = auditar_integridad_v3(db)
        preflight = PreflightMotorPagoV3(
            db,
            version_minima=13,
            ejecuciones_minimas=args.min_runs,
            tasa_coincidencia_minima=Decimal(args.min_match),
            divergencias_maximas=args.max_divergences,
            errores_maximos=args.max_errors,
        ).evaluar()
        estado = ServicioConfiguracionMotorPago(db).obtener()
        metricas = ServicioMetricasSombraV3(db).obtener()

        modo_compatible = estado.modo.value in {"LEGACY", "SOMBRA"}
        listo = integridad.ok and preflight.apto and modo_compatible

        payload = {
            "database": str(db_path.resolve()),
            "listo_para_canary": listo,
            "modo_actual": estado.modo.value,
            "revision_modo": estado.revision,
            "integridad_ok": integridad.ok,
            "preflight_apto": preflight.apto,
            "evidencia_sombra": {
                "ejecuciones": metricas.ejecuciones_sombra,
                "coincidencia": metricas.tasa_coincidencia,
                "divergencias": metricas.ejecuciones_con_divergencia,
                "errores": metricas.ejecuciones_con_error,
            },
            "motivos_rechazo": list(preflight.motivos_rechazo),
        }

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if listo else 2


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    try:
        return ejecutar(args.db, args)
    except Exception as exc:
        print(
            json.dumps(
                {"listo_para_canary": False, "error": f"{type(exc).__name__}: {exc}"},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
