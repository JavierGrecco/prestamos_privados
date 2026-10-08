"""Pruebas del contrato auto-descriptivo de la evidencia de canary."""
from pathlib import Path
import json

from scripts.canary_precheck_motor_pago_v3 import main
from tests.test_canary_precheck import crear_db


def test_evidencia_expone_formato_y_politica(tmp_path: Path, capsys):
    ruta = tmp_path / "canary.db"
    salida = tmp_path / "evidencia.json"
    crear_db(ruta, 100)

    codigo = main([
        str(ruta),
        "--min-runs", "100",
        "--min-match", "1",
        "--max-divergences", "0",
        "--max-errors", "0",
        "--output", str(salida),
    ])
    stdout = capsys.readouterr().out
    payload = json.loads(salida.read_text(encoding="utf-8"))

    assert codigo == 0
    assert stdout == salida.read_text(encoding="utf-8")
    assert payload["evidence_format_version"] == 1
    assert payload["evaluator"] == "canary_precheck_motor_pago_v3"
    assert payload["politica"] == {
        "schema_minimo": 13,
        "ejecuciones_minimas": 100,
        "tasa_coincidencia_minima": "1",
        "divergencias_maximas": 0,
        "errores_maximos": 0,
    }


def test_publicacion_temporal_no_deja_archivos_tmp(tmp_path: Path, capsys):
    ruta = tmp_path / "canary.db"
    salida = tmp_path / "nested" / "evidencia.json"
    crear_db(ruta, 100)

    assert main([
        str(ruta),
        "--min-runs", "100",
        "--output", str(salida),
    ]) == 0
    capsys.readouterr()

    assert salida.exists()
    assert not list(salida.parent.glob(f".{salida.name}.*.tmp"))
