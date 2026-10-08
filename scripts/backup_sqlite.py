#!/usr/bin/env python3
"""CLI mínima para operaciones verificables de SQLite.

Ejemplos:
    python scripts/backup_sqlite.py integrity datos/prestamos.db
    python scripts/backup_sqlite.py create datos/prestamos.db backups/prestamos-001.db
    python scripts/backup_sqlite.py verify backups/prestamos-001.db
    python scripts/backup_sqlite.py restore backups/prestamos-001.db restore/prestamos.db
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from infraestructura.backup import (
    crear_backup_verificado,
    restaurar_backup_verificado,
    verificar_backup,
    verificar_integridad_sqlite,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backup, restore y health check verificables de SQLite."
    )
    subparsers = parser.add_subparsers(dest="operacion", required=True)

    integrity = subparsers.add_parser("integrity", help="verificar una base")
    integrity.add_argument("ruta")

    create = subparsers.add_parser("create", help="crear un backup")
    create.add_argument("origen")
    create.add_argument("backup")

    verify = subparsers.add_parser("verify", help="verificar un backup")
    verify.add_argument("backup")

    restore = subparsers.add_parser("restore", help="restaurar a una ruta nueva")
    restore.add_argument("backup")
    restore.add_argument("destino")
    return parser


def main() -> int:
    args = _parser().parse_args()

    if args.operacion == "integrity":
        resultado = verificar_integridad_sqlite(args.ruta)
    elif args.operacion == "create":
        resultado = crear_backup_verificado(args.origen, args.backup)
    elif args.operacion == "verify":
        resultado = verificar_backup(args.backup)
    else:
        resultado = restaurar_backup_verificado(args.backup, args.destino)

    print(json.dumps(_normalizar(resultado), ensure_ascii=False, indent=2))
    return 0


def _normalizar(resultado) -> dict:
    if hasattr(resultado, "integridad"):
        integridad = resultado.integridad
        salida = {
            "ok": integridad.ok,
            "ruta": str(getattr(resultado, "ruta_backup", getattr(resultado, "ruta_restore", ""))),
            "bytes": getattr(resultado, "bytes", 0),
        }
        if hasattr(resultado, "sha256"):
            salida["sha256"] = resultado.sha256
        if hasattr(resultado, "ruta_manifest"):
            salida["manifest"] = str(resultado.ruta_manifest)
        return salida

    return {
        "ok": resultado.ok,
        "ruta": str(resultado.ruta),
        "quick_check": resultado.quick_check,
        "integrity_check": resultado.integrity_check,
        "foreign_key_errores": len(resultado.foreign_key_errores),
    }


if __name__ == "__main__":
    raise SystemExit(main())
