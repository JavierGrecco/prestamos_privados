#!/usr/bin/env python3
"""Restore drill reproducible con datos sintéticos del dominio de préstamos.

Crea una base aislada, registra un préstamo y un pago mediante servicios de
aplicación, genera/verifica un backup, restaura a otra ruta y compara la
estructura y los registros. Nunca abre ni modifica PRESTAMOS_DB_PATH.
"""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from infraestructura import BaseDatos, ErrorBackup, crear_backup_verificado, restaurar_backup_verificado, verificar_backup, verificar_integridad_sqlite
from infraestructura.composicion.prestamos import crear_servicio_prestamos
from infraestructura.composicion.servicio_pagos_legacy import crear_servicio_pagos_legacy
from infraestructura.migraciones import aplicar_migraciones, version_destino_migraciones
from infraestructura.repositorios import LedgerRepo, PersonaRepo, PrestamoRepo

FECHA_INICIO = date(2026, 1, 1)
FECHA_PAGO = date(2026, 2, 1)
USUARIO = "restore-drill-sintetico"
TABLAS = {
    "migraciones": "version",
    "personas": "id",
    "roles_persona": "persona_id, rol",
    "prestamos": "id",
    "versiones_tasa": "id",
    "cuotas": "id",
    "participaciones": "id",
    "pagos": "id",
    "imputaciones": "id",
    "ledger": "id",
    "auditoria": "id",
    "correcciones_auditables": "id",
}


def _sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _snapshot(ruta: Path) -> dict:
    """Lee la base en modo solo lectura y captura esquema + hechos económicos."""
    uri = ruta.resolve().as_uri() + "?mode=ro"
    conexion = sqlite3.connect(uri, uri=True)
    try:
        schema = tuple(
            tuple(fila)
            for fila in conexion.execute(
                """
                SELECT type, name, sql
                FROM sqlite_master
                WHERE type IN ('table', 'index', 'trigger')
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY type, name
                """
            )
        )
        tablas = {}
        for tabla, orden in TABLAS.items():
            tablas[tabla] = tuple(
                tuple(fila)
                for fila in conexion.execute(
                    f"SELECT * FROM {tabla} ORDER BY {orden}"
                )
            )
        secuencias = tuple(
            tuple(fila)
            for fila in conexion.execute(
                "SELECT name, seq FROM sqlite_sequence ORDER BY name"
            )
        )
        versiones = tuple(
            str(fila[0]) for fila in conexion.execute("PRAGMA user_version")
        )
        integridad = tuple(
            str(fila[0]) for fila in conexion.execute("PRAGMA integrity_check")
        )
        claves = tuple(
            tuple(fila) for fila in conexion.execute("PRAGMA foreign_key_check")
        )
    finally:
        conexion.close()
    return {
        "schema": schema,
        "tablas": tablas,
        "secuencias": secuencias,
        "user_version": versiones,
        "integrity_check": integridad,
        "foreign_key_check": claves,
    }


def _crear_operacion_sintetica(origen: Path) -> tuple[int, int]:
    """Crea datos por los mismos servicios de aplicación que usa el producto."""
    with BaseDatos(origen) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor_id = personas.crear(
            nombre="Deudor",
            apellido="Restore Drill",
        )
        personas.agregar_rol(deudor_id, "DEUDOR")
        inversor_id = personas.crear(
            nombre="Inversor",
            apellido="Restore Drill",
        )
        personas.agregar_rol(inversor_id, "INVERSOR")

        prestamo_id = crear_servicio_prestamos(db).crear_completo(
            deudor_id=deudor_id,
            capital=Decimal("10000.00"),
            plazo_meses=3,
            tasa_anual=Decimal("0.24"),
            modalidad_tasa="TNA",
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=FECHA_INICIO,
            inversores=[
                {"persona_id": inversor_id, "monto": Decimal("10000.00")}
            ],
            usuario=USUARIO,
            destino="Prueba sintética de recuperación",
        )

        pagos = crear_servicio_pagos_legacy(db)
        deuda = pagos.calcular_deuda_proximo_pago(prestamo_id, FECHA_PAGO)
        if deuda is None:
            raise RuntimeError("No se pudo calcular la primera cuota sintética")
        monto = Decimal(str(deuda["total_a_pagar"]))
        pago_id = pagos.registrar_pago(
            prestamo_id=prestamo_id,
            monto=monto,
            fecha_real=FECHA_PAGO,
            fecha_valor=FECHA_PAGO,
            usuario=USUARIO,
            medio="Transferencia sintética",
            referencia="RESTORE-DRILL-001",
            nota="Movimiento generado exclusivamente para el restore drill",
        )
        if not LedgerRepo(db).verificar_cuadre():
            raise RuntimeError("El ledger sintético no está cuadrado")
    return prestamo_id, pago_id


def ejecutar_drill(directorio: str | Path) -> dict:
    root = Path(directorio).expanduser().absolute()
    if root.exists():
        raise FileExistsError(
            f"El directorio destino ya existe; se exige una ruta nueva: {root}"
        )
    root.mkdir(parents=True)

    origen = root / "origen_sintetico.db"
    backup = root / "backup" / "prestamos.db"
    restore = root / "restore" / "prestamos_restaurados.db"
    backup_corrupto = root / "corrupto" / "prestamos.db"
    restore_corrupto = root / "corrupto" / "restore.db"

    prestamo_id, pago_id = _crear_operacion_sintetica(origen)
    snapshot_origen = _snapshot(origen)
    hash_origen_antes = _sha256(origen)

    evidencia_backup = crear_backup_verificado(origen, backup)
    evidencia_verificada = verificar_backup(backup)
    evidencia_restore = restaurar_backup_verificado(backup, restore)

    snapshot_restore = _snapshot(restore)
    snapshot_origen_despues = _snapshot(origen)
    hash_origen_despues = _sha256(origen)

    # Reabrir mediante la infraestructura real y consultar el préstamo restaurado.
    with BaseDatos(restore) as db:
        prestamo = PrestamoRepo(db).obtener(prestamo_id)
        if prestamo is None:
            raise RuntimeError("La aplicación no pudo volver a leer el préstamo restaurado")
        if not LedgerRepo(db).verificar_cuadre():
            raise RuntimeError("El ledger restaurado no conserva el cuadre")
        version = db.consultar_uno(
            "SELECT MAX(version) AS version FROM migraciones"
        )["version"]
        integridad_app = db.verificar_integridad_completa()

    # El camino negativo usa una copia alterada; el backup original queda intacto.
    backup_corrupto.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(backup, backup_corrupto)
    shutil.copyfile(
        backup.with_name(backup.name + ".manifest.json"),
        backup_corrupto.with_name(backup_corrupto.name + ".manifest.json"),
    )
    with backup_corrupto.open("ab") as archivo:
        archivo.write(b"alteracion-intencional-del-drill")

    corrupto_rechazado = False
    try:
        restaurar_backup_verificado(backup_corrupto, restore_corrupto)
    except ErrorBackup:
        corrupto_rechazado = True

    filas = {
        tabla: len(registros)
        for tabla, registros in snapshot_origen["tablas"].items()
    }
    origen_inalterado = (
        hash_origen_antes == hash_origen_despues
        and snapshot_origen == snapshot_origen_despues
    )
    restore_coincide = snapshot_origen == snapshot_restore
    if not origen_inalterado:
        raise RuntimeError("El archivo de origen cambió durante el drill")
    if not restore_coincide:
        raise RuntimeError("El restore no coincide con el snapshot del origen")
    if not corrupto_rechazado or restore_corrupto.exists():
        raise RuntimeError("No se rechazó correctamente el backup alterado")
    if version != version_destino_migraciones():
        raise RuntimeError(
            f"El esquema restaurado es v{version}; se esperaba "
            f"v{version_destino_migraciones()}"
        )
    if not integridad_app or not evidencia_backup.integridad.ok:
        raise RuntimeError("La aplicación o el backup no superaron integridad")

    if filas["personas"] != 2 or filas["prestamos"] != 1:
        raise RuntimeError("La fixture sintética no contiene las dos personas y un préstamo")
    if filas["participaciones"] != 1 or filas["pagos"] != 1:
        raise RuntimeError("Falta la participación o el pago sintético")
    if not filas["ledger"] or not filas["auditoria"]:
        raise RuntimeError("Falta evidencia de ledger o auditoría")

    return {
        "ok": True,
        "esquema": version,
        "prestamo_id": prestamo_id,
        "pago_id": pago_id,
        "filas": filas,
        "integridad_backup": evidencia_verificada.integridad.ok,
        "integridad_restore": evidencia_restore.integridad.ok,
        "ledger_cuadrado": True,
        "origen_inalterado": origen_inalterado,
        "restore_coincide_con_origen": restore_coincide,
        "backup_alterado_rechazado": corrupto_rechazado,
        "sha256_origen": hash_origen_antes,
        "sha256_backup": evidencia_verificada.sha256,
        "sha256_restore": evidencia_restore.sha256,
        "rutas": {
            "origen_sintetico": str(origen),
            "backup_verificado": str(backup),
            "restore": str(restore),
            "backup_corrupto_de_prueba": str(backup_corrupto),
        },
        "comando_apertura_manual": (
            f'PRESTAMOS_DB_PATH="{restore}" streamlit run ui/app.py'
        ),
        "aceptacion_ui_manual_pendiente": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Crea una base sintética, ejecuta backup/restore y compara "
            "integridad, datos económicos y evidencia."
        )
    )
    parser.add_argument(
        "--directorio",
        required=True,
        help="Directorio nuevo donde quedarán origen, backup, restore y copia corrupta",
    )
    args = parser.parse_args(argv)
    try:
        resultado = ejecutar_drill(args.directorio)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": type(exc).__name__,
                    "detalle": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
