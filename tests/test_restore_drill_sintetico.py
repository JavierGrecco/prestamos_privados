"""Pruebas del restore drill con datos sintéticos del dominio real."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
from streamlit.testing.v1 import AppTest

from infraestructura import BaseDatos
from infraestructura.repositorios import LedgerRepo, PrestamoRepo
from tests.ui_auth_helpers import iniciar_apptest_autenticado

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "restore_drill_sintetico.py"
APP = ROOT / "ui" / "app.py"


def test_restore_drill_real_compara_origen_restore_y_rechaza_backup_corrupto(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destino = tmp_path / "drill"
    proceso = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--directorio",
            str(destino),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )

    assert proceso.returncode == 0, proceso.stderr or proceso.stdout
    resultado = json.loads(proceso.stdout)

    assert resultado["ok"] is True
    assert resultado["esquema"] == 26
    assert resultado["filas"]["personas"] == 2
    assert resultado["filas"]["roles_persona"] == 2
    assert resultado["filas"]["prestamos"] == 1
    assert resultado["filas"]["versiones_tasa"] == 1
    assert resultado["filas"]["cuotas"] == 3
    assert resultado["filas"]["participaciones"] == 1
    assert resultado["filas"]["pagos"] == 1
    assert resultado["filas"]["imputaciones"] >= 1
    assert resultado["filas"]["ledger"] >= 2
    assert resultado["filas"]["auditoria"] >= 3
    assert resultado["integridad_backup"] is True
    assert resultado["integridad_restore"] is True
    assert resultado["ledger_cuadrado"] is True
    assert resultado["origen_inalterado"] is True
    assert resultado["restore_coincide_con_origen"] is True
    assert resultado["backup_alterado_rechazado"] is True
    assert resultado["aceptacion_ui_manual_pendiente"] is True

    rutas = resultado["rutas"]
    assert Path(rutas["origen_sintetico"]).is_file()
    assert Path(rutas["backup_verificado"]).is_file()
    assert Path(rutas["restore"]).is_file()
    assert Path(rutas["backup_corrupto_de_prueba"]).is_file()
    assert len(resultado["sha256_origen"]) == 64
    assert resultado["sha256_backup"] == resultado["sha256_restore"]

    # La aplicación real debe poder abrir la copia restaurada, no solo los
    # repositorios. Se apunta explícitamente a restore; nunca a la base local.
    ruta_restore = Path(rutas["restore"])
    monkeypatch.setenv("PRESTAMOS_DB_PATH", str(ruta_restore))
    monkeypatch.setenv("PRESTAMOS_AUTH_MODE", "local")

    primera_sesion = AppTest.from_file(APP, default_timeout=15)
    primera_sesion.run()
    assert not primera_sesion.exception
    assert any(
        titulo.value == "Configurar administrador local"
        for titulo in primera_sesion.title
    )

    iniciar_apptest_autenticado(primera_sesion, ruta_restore)
    assert any(
        "admin · ADMIN" in str(caption.value)
        for caption in primera_sesion.caption
    )

    # Un contexto nuevo debe reconocer la cuenta ya creada en la copia
    # restaurada y ofrecer login, no volver a configurar otro administrador.
    sesion_nueva = AppTest.from_file(APP, default_timeout=15)
    sesion_nueva.run()
    assert not sesion_nueva.exception
    assert any(
        titulo.value == "Iniciar sesión"
        for titulo in sesion_nueva.title
    )
    assert not any(
        titulo.value == "Configurar administrador local"
        for titulo in sesion_nueva.title
    )

    iniciar_apptest_autenticado(sesion_nueva, ruta_restore)
    assert any(
        "admin · ADMIN" in str(caption.value)
        for caption in sesion_nueva.caption
    )

    with BaseDatos(ruta_restore) as db:
        prestamo = PrestamoRepo(db).obtener(resultado["prestamo_id"])
        cantidad_pagos = db.consultar_uno(
            "SELECT COUNT(*) AS cantidad FROM pagos"
        )["cantidad"]
        assert prestamo is not None
        assert cantidad_pagos == 1
        assert LedgerRepo(db).verificar_cuadre()


def test_restore_drill_no_usa_ni_sobrescribe_directorio_existente(
    tmp_path: Path,
) -> None:
    destino = tmp_path / "destino-existente"
    destino.mkdir()
    sentinel = destino / "no_tocar.db"
    sentinel.write_bytes(b"datos ajenos")

    proceso = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--directorio",
            str(destino),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert proceso.returncode == 1
    resultado = json.loads(proceso.stderr)
    assert resultado["ok"] is False
    assert resultado["error"] == "FileExistsError"
    assert sentinel.read_bytes() == b"datos ajenos"
