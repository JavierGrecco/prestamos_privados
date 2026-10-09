"""Restablecimiento offline de la contraseña de una cuenta ADMIN local.

Este comando requiere acceso al sistema de archivos y a la base SQLite local.
No es un flujo web ni envía correo. Para otras cuentas, usá el panel ADMIN.
"""

from __future__ import annotations

import argparse
from getpass import getpass
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aplicacion.servicios.usuarios_locales import ServicioUsuariosLocales
from infraestructura import BaseDatos


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Restablece offline la contraseña de una cuenta ADMIN activa. "
            "Requiere acceso a la base local."
        )
    )
    parser.add_argument("db", type=Path, help="Ruta a la base SQLite.")
    parser.add_argument(
        "--usuario",
        default="admin",
        help="Nombre de cuenta ADMIN que se desea recuperar (por defecto: admin).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    ruta = args.db.expanduser().resolve()
    if not ruta.is_file():
        print(
            json.dumps(
                {"ok": False, "error": f"No existe la base local: {ruta}"},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    password = getpass("Nueva contraseña (mínimo 12 caracteres): ")
    confirmacion = getpass("Repetir nueva contraseña: ")
    if password != confirmacion:
        print(json.dumps({"ok": False, "error": "Las contraseñas no coinciden."}))
        return 2

    try:
        with BaseDatos(ruta) as db:
            servicio = ServicioUsuariosLocales(db)
            servicio.restablecer_password_por_acceso_local(
                username=args.usuario,
                password_nueva=password,
            )
    except Exception as exc:
        print(
            json.dumps(
                {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "usuario": args.usuario.strip().lower(),
                "detalle": (
                    "Contraseña actualizada. El secreto no se mostró ni se guardó "
                    "en el historial de auditoría."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
