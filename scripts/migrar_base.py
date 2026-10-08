"""Inspección y migración explícita de bases SQLite.

Por defecto el comando solo inspecciona el historial y no ejecuta migraciones.

Ejemplos:
    python -m scripts.migrar_base datos/prestamos.db
    python -m scripts.migrar_base datos/prestamos.db --aplicar --backup backups/prestamos-pre-migracion.db
    python -m scripts.migrar_base datos/nueva.db --aplicar
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from infraestructura import BaseDatos, crear_backup_verificado
from infraestructura.migraciones import (
    EstadoMigraciones,
    aplicar_migraciones,
    inspeccionar_estado_migraciones,
    listar_migraciones_planeadas,
)


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspecciona el schema SQLite y aplica migraciones solo cuando "
            "se solicita expresamente."
        )
    )
    parser.add_argument("db", type=Path, help="Ruta de la base SQLite.")
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Aplicar las migraciones pendientes. Sin esta opción solo inspecciona.",
    )
    parser.add_argument(
        "--backup",
        type=Path,
        help=(
            "Ruta nueva para un backup verificado obligatorio al actualizar "
            "una base existente. No se sobrescriben archivos."
        ),
    )
    return parser


def _payload_estado(ruta: Path, estado: EstadoMigraciones) -> dict[str, Any]:
    return {
        "base": str(ruta),
        "resultado": "INSPECCION",
        "es_base_nueva": estado.es_base_nueva,
        "historial_valido": estado.historial_valido,
        "version_origen": estado.version_actual,
        "version_destino": estado.version_destino,
        "migraciones_pendientes": [
            {"version": m.version, "nombre": m.nombre}
            for m in estado.pendientes
        ],
        "detalle": estado.detalle,
        "cambios_aplicados": [],
    }


def _emitir(payload: dict[str, Any], codigo: int) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return codigo


def ejecutar(args: argparse.Namespace) -> int:
    ruta = args.db.expanduser().resolve()
    ruta_backup = args.backup.expanduser().resolve() if args.backup else None

    if ruta_backup is not None and not args.aplicar:
        return _emitir(
            {
                "base": str(ruta),
                "resultado": "RECHAZADO",
                "error": "--backup requiere la opción --aplicar.",
            },
            2,
        )

    if not ruta.exists() and not args.aplicar:
        pendientes = listar_migraciones_planeadas()
        return _emitir(
            {
                "base": str(ruta),
                "resultado": "BASE_INEXISTENTE",
                "es_base_nueva": True,
                "historial_valido": True,
                "version_origen": None,
                "version_destino": max((m.version for m in pendientes), default=0),
                "migraciones_pendientes": [
                    {"version": m.version, "nombre": m.nombre}
                    for m in pendientes
                ],
                "detalle": "La inspección no creó el archivo ni modificó el schema.",
                "cambios_aplicados": [],
            },
            0,
        )

    evidencia_backup: dict[str, Any] | None = None
    try:
        with BaseDatos(ruta) as db:
            estado = inspeccionar_estado_migraciones(db)
            payload = _payload_estado(ruta, estado)

            if not estado.historial_valido:
                payload["resultado"] = "RECHAZADO_HISTORIAL"
                payload["error"] = estado.detalle or (
                    "El historial de migraciones no permite una actualización segura."
                )
                return _emitir(payload, 2)

            if not args.aplicar:
                payload["resultado"] = (
                    "REQUIERE_MIGRACION"
                    if estado.pendientes
                    else "ACTUALIZADA"
                )
                return _emitir(payload, 0)

            if not estado.pendientes:
                payload["resultado"] = "SIN_CAMBIOS"
                payload["detalle"] = "La base ya está en la versión objetivo."
                return _emitir(payload, 0)

            if not estado.es_base_nueva:
                if ruta_backup is None:
                    payload["resultado"] = "BACKUP_REQUERIDO"
                    payload["error"] = (
                        "Para actualizar una base existente se exige --backup "
                        "con una ruta nueva. No se aplicó ninguna migración."
                    )
                    return _emitir(payload, 2)

                backup = crear_backup_verificado(ruta, ruta_backup)
                evidencia_backup = {
                    "ruta": str(backup.ruta_backup),
                    "manifiesto": str(backup.ruta_manifest),
                    "sha256": backup.sha256,
                    "bytes": backup.bytes,
                    "integridad_ok": backup.integridad.ok,
                }
                if not backup.integridad.ok:
                    payload["resultado"] = "BACKUP_NO_VALIDO"
                    payload["error"] = (
                        "El backup no superó las verificaciones; se canceló "
                        "la actualización."
                    )
                    payload["backup"] = evidencia_backup
                    return _emitir(payload, 1)

            try:
                aplicadas = aplicar_migraciones(db)
            except Exception as exc:
                payload["resultado"] = "ERROR_MIGRACION"
                payload["error"] = f"{type(exc).__name__}: {exc}"
                payload["backup"] = evidencia_backup
                return _emitir(payload, 1)

            estado_final = inspeccionar_estado_migraciones(db)
            payload_final = _payload_estado(ruta, estado_final)
            payload_final["cambios_aplicados"] = aplicadas
            payload_final["backup"] = evidencia_backup
            payload_final["resultado"] = (
                "APLICADA"
                if estado_final.historial_valido and not estado_final.pendientes
                else "ERROR_ESTADO_FINAL"
            )
            if payload_final["resultado"] != "APLICADA":
                payload_final["error"] = (
                    estado_final.detalle
                    or "La base no alcanzó la versión objetivo."
                )
                return _emitir(payload_final, 1)
            return _emitir(payload_final, 0)
    except Exception as exc:
        return _emitir(
            {
                "base": str(ruta),
                "resultado": "ERROR_OPERATIVO",
                "error": f"{type(exc).__name__}: {exc}",
                "backup": evidencia_backup,
            },
            1,
        )


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    return ejecutar(args)


if __name__ == "__main__":
    raise SystemExit(main())
