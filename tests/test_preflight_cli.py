"""Tests del informe reproducible de preflight V3."""

from decimal import Decimal
from pathlib import Path

from scripts.preflight_motor_pago_v3 import main
from aplicacion.servicios.puente_motor_pago_v3 import (
    EjecucionSombraMotorPagoV3,
    ResultadoEjecucionSombraV3,
)
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios.ejecuciones_sombra_v3 import EjecucionesSombraV3Repo


def _crear_db(path: Path, *, cantidad: int, resultado=ResultadoEjecucionSombraV3.SIN_DIVERGENCIA):
    with BaseDatos(path) as db:
        aplicar_migraciones(db)
        repo = EjecucionesSombraV3Repo(db)
        for i in range(cantidad):
            repo.registrar(
                EjecucionSombraMotorPagoV3(
                    fingerprint=f"fp-{i}",
                    prestamo_id=1,
                    pago_legacy_id=None,
                    resultado=resultado,
                    revision_snapshot=0,
                    resumen=None,
                )
            )


def test_cli_aprueba_con_evidencia_suficiente(tmp_path: Path, capsys):
    ruta = tmp_path / "preflight.db"
    _crear_db(ruta, cantidad=10)

    codigo = main([
        str(ruta),
        "--min-runs", "10",
        "--min-match", "1",
    ])

    salida = capsys.readouterr().out
    assert codigo == 0
    assert '"apto": true' in salida
    assert '"nombre": "ejecuciones_minimas"' in salida


def test_cli_rechaza_sin_evidencia_suficiente(tmp_path: Path, capsys):
    ruta = tmp_path / "preflight.db"
    _crear_db(ruta, cantidad=2)

    codigo = main([str(ruta)])

    salida = capsys.readouterr().out
    assert codigo == 2
    assert '"apto": false' in salida
    assert "Ejecuciones SOMBRA: 2; mínimo: 100" in salida


def test_cli_es_solo_lectura(tmp_path: Path, capsys):
    ruta = tmp_path / "preflight.db"
    _crear_db(ruta, cantidad=1)

    with BaseDatos(ruta) as db:
        antes = db.consultar_uno(
            "SELECT COUNT(*) AS n FROM ejecuciones_sombra_v3"
        )["n"]

    codigo = main([
        str(ruta),
        "--min-runs", "1",
        "--min-match", "1",
    ])

    capsys.readouterr()
    assert codigo == 0

    with BaseDatos(ruta) as db:
        despues = db.consultar_uno(
            "SELECT COUNT(*) AS n FROM ejecuciones_sombra_v3"
        )["n"]

    assert despues == antes
