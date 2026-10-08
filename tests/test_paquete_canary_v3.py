"""Pruebas del paquete de decisión de canary V3."""

import json
from pathlib import Path

import pytest

from aplicacion.servicios.paquete_canary_v3 import ServicioPaqueteCanaryV3
from infraestructura import BaseDatos
from infraestructura.backup import ErrorBackup, crear_backup_verificado
from scripts.paquete_decision_canary_v3 import main
from tests.test_canary_precheck import crear_db


def test_paquete_apto_reune_backup_y_readiness(tmp_path: Path):
    ruta = tmp_path / "canary.db"
    backup = tmp_path / "backup.db"
    crear_db(ruta, 100)
    with BaseDatos(ruta) as db:
        antes = dict(
            db.consultar_uno(
                "SELECT modo, revision FROM configuracion_motor_pago WHERE id = 1"
            )
        )
        evidencia = crear_backup_verificado(ruta, backup)

        paquete = ServicioPaqueteCanaryV3(db).evaluar(
            base_path=ruta,
            backup_path=backup,
            operador="operador-canary",
            motivo_revision="Revisión previa controlada",
        )

        despues = dict(
            db.consultar_uno(
                "SELECT modo, revision FROM configuracion_motor_pago WHERE id = 1"
            )
        )

    assert paquete.apto_para_revision_humana is True
    assert paquete.backup_integridad_ok is True
    assert paquete.backup_sha256 == evidencia.sha256
    assert paquete.readiness.listo is True
    assert paquete.readiness.modo_actual == "SOMBRA"
    assert paquete.operador == "operador-canary"
    assert paquete.motivo_revision == "Revisión previa controlada"
    assert despues == antes


def test_paquete_bloquea_backup_invalido(tmp_path: Path):
    ruta = tmp_path / "canary.db"
    backup = tmp_path / "backup.db"
    crear_db(ruta, 100)
    backup.write_bytes(b"esto no es sqlite")

    with BaseDatos(ruta) as db:
        with pytest.raises(ErrorBackup):
            ServicioPaqueteCanaryV3(db).evaluar(
                base_path=ruta,
                backup_path=backup,
                operador="operador",
                motivo_revision="Prueba de rechazo",
            )


def test_cli_guarda_paquete_sin_sobrescribir(tmp_path: Path, capsys):
    ruta = tmp_path / "canary.db"
    backup = tmp_path / "backup.db"
    salida = tmp_path / "paquete.json"
    crear_db(ruta, 100)

    crear_backup_verificado(ruta, backup)

    codigo = main(
        [
            str(ruta),
            str(backup),
            "--operador",
            "operador-canary",
            "--motivo",
            "Revisión L1.2",
            "--min-runs",
            "100",
            "--output",
            str(salida),
        ]
    )
    stdout = capsys.readouterr().out

    assert codigo == 0
    payload = json.loads(salida.read_text(encoding="utf-8"))
    assert payload["apto_para_revision_humana"] is True
    assert payload["readiness"]["listo"] is True
    assert payload["backup_sha256"]

    salida.write_text("evidencia anterior\n", encoding="utf-8")
    codigo2 = main(
        [
            str(ruta),
            str(backup),
            "--operador",
            "operador-canary",
            "--motivo",
            "Segundo intento",
            "--output",
            str(salida),
        ]
    )
    stdout2 = capsys.readouterr().out

    assert codigo2 == 1
    assert salida.read_text(encoding="utf-8") == "evidencia anterior\n"
    assert "Ya existe el paquete" in stdout2
