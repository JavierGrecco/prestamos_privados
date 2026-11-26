"""Contrato del manifiesto para retirar ramas históricas sin perder el control."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "branch-retirement-manifest.json"


def test_manifiesto_tiene_solo_retiros_explicitos_con_sha_y_motivo():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["version"] == 1
    entries = data["branches"]
    names = [entry["name"] for entry in entries]

    assert len(entries) == 14
    assert len(names) == len(set(names))
    assert "main" not in names
    assert "review/m5-rendimiento-operaciones" not in names
    for entry in entries:
        assert re.fullmatch(r"[0-9a-f]{40}", entry["expected_sha"])
        assert entry["reason"].strip()


def test_fuente_m5_se_conserva_bajo_una_referencia_de_revision():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    retired = {
        entry["name"]: entry["expected_sha"]
        for entry in data["branches"]
    }

    assert retired["feature/m5-rendimiento-operaciones"] == (
        "99eabec19c2ab6c2c7dc2c4b217d52818589e04c"
    )
