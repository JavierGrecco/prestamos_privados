"""Pruebas de protección de artefactos de evidencia del canary."""

from pathlib import Path

from scripts.canary_precheck_motor_pago_v3 import main
from tests.test_canary_precheck import crear_db


def test_evidencia_existente_no_se_sobrescribe_sin_force(tmp_path: Path, capsys):
    ruta = tmp_path / "canary.db"
    salida = tmp_path / "evidencia.json"
    crear_db(ruta, 100)
    contenido_original = '{ "evidencia": "anterior" }\n'
    salida.write_text(contenido_original, encoding="utf-8")

    codigo = main([
        str(ruta),
        "--min-runs",
        "100",
        "--output",
        str(salida),
    ])
    salida_stdout = capsys.readouterr().out

    assert codigo == 1
    assert salida.read_text(encoding="utf-8") == contenido_original
    assert salida_stdout.count("\"evidence_format_version\"") == 0
    assert "FileExistsError" in salida_stdout
    assert "Ya existe el artefacto de evidencia" in salida_stdout


def test_force_output_permite_reemplazo_explicito(tmp_path: Path, capsys):
    ruta = tmp_path / "canary-force.db"
    salida = tmp_path / "evidencia-force.json"
    crear_db(ruta, 100)
    salida.write_text("evidencia vieja\n", encoding="utf-8")

    codigo = main([
        str(ruta),
        "--min-runs",
        "100",
        "--output",
        str(salida),
        "--force-output",
    ])
    stdout = capsys.readouterr().out
    guardado = salida.read_text(encoding="utf-8")

    assert codigo == 0
    assert guardado == stdout
    assert '"listo_para_canary": true' in guardado
    assert "evidencia vieja" not in guardado
