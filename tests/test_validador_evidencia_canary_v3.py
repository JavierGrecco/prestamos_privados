"""Pruebas del validador de evidencia de canary V3."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from aplicacion.servicios.validador_evidencia_canary_v3 import (
    ValidadorEvidenciaCanaryV3,
)
from infraestructura import BaseDatos
from infraestructura.backup import crear_backup_verificado
from infraestructura.migraciones import aplicar_migraciones


def _crear_db(path: Path) -> None:
    with BaseDatos(path) as db:
        aplicar_migraciones(db)


def _readiness(
    path: Path,
    *,
    evaluado_en: datetime | None = None,
    runs: int = 100,
    match: float = 1.0,
    divergencias: int = 0,
    errores: int = 0,
    runs_policy: int = 100,
) -> None:
    fecha = (evaluado_en or datetime.now(timezone.utc)).isoformat()
    payload = {
        "evidence_format_version": 1,
        "evaluated_at": fecha,
        "listo_para_canary": True,
        "modo_actual": "LEGACY",
        "integridad_ok": True,
        "preflight_apto": True,
        "motivos_rechazo": [],
        "politica": {
            "schema_minimo": 13,
            "ejecuciones_minimas": runs_policy,
            "tasa_coincidencia_minima": 1.0,
            "divergencias_maximas": 0,
            "errores_maximos": 0,
        },
        "evidencia_sombra": {
            "ejecuciones": runs,
            "coincidencia": match,
            "divergencias": divergencias,
            "errores": errores,
        },
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "
",
        encoding="utf-8",
    )


def test_paquete_valido(tmp_path: Path):
    origen = tmp_path / "origen.db"
    backup = tmp_path / "backup.db"
    readiness = tmp_path / "readiness.json"

    _crear_db(origen)
    crear_backup_verificado(origen, backup)
    _readiness(readiness)

    resultado = ValidadorEvidenciaCanaryV3().validar(
        readiness,
        backup,
    )

    assert resultado.apto
    assert resultado.formato_ok
    assert resultado.readiness_ok
    assert resultado.backup_ok
    assert resultado.antiguedad_ok
    assert resultado.sha256_backup


def test_rechaza_evidencia_vencida(tmp_path: Path):
    origen = tmp_path / "origen.db"
    backup = tmp_path / "backup.db"
    readiness = tmp_path / "readiness.json"

    _crear_db(origen)
    crear_backup_verificado(origen, backup)
    _readiness(
        readiness,
        evaluado_en=datetime.now(timezone.utc) - timedelta(hours=25),
    )

    resultado = ValidadorEvidenciaCanaryV3(max_edad_horas=24).validar(
        readiness,
        backup,
    )

    assert not resultado.apto
    assert not resultado.antiguedad_ok
    assert any("antigüedad" in x for x in resultado.motivos_rechazo)


def test_rechaza_politica_relajada(tmp_path: Path):
    origen = tmp_path / "origen.db"
    backup = tmp_path / "backup.db"
    readiness = tmp_path / "readiness.json"

    _crear_db(origen)
    crear_backup_verificado(origen, backup)
    _readiness(
        readiness,
        runs=100,
        runs_policy=10,
    )

    resultado = ValidadorEvidenciaCanaryV3(
        ejecuciones_minimas=100,
    ).validar(readiness, backup)

    assert not resultado.apto
    assert any("política de ejecuciones" in x for x in resultado.motivos_rechazo)


def test_rechaza_divergencia(tmp_path: Path):
    origen = tmp_path / "origen.db"
    backup = tmp_path / "backup.db"
    readiness = tmp_path / "readiness.json"

    _crear_db(origen)
    crear_backup_verificado(origen, backup)
    _readiness(readiness, divergencias=1)

    resultado = ValidadorEvidenciaCanaryV3().validar(
        readiness,
        backup,
    )

    assert not resultado.apto
    assert any("Divergencias" in x for x in resultado.motivos_rechazo)


def test_rechaza_backup_alterado(tmp_path: Path):
    origen = tmp_path / "origen.db"
    backup = tmp_path / "backup.db"
    readiness = tmp_path / "readiness.json"

    _crear_db(origen)
    crear_backup_verificado(origen, backup)
    _readiness(readiness)

    with backup.open("ab") as archivo:
        archivo.write(b"alterado")

    resultado = ValidadorEvidenciaCanaryV3().validar(
        readiness,
        backup,
    )

    assert not resultado.apto
    assert not resultado.backup_ok
    assert any("backup" in x.lower() for x in resultado.motivos_rechazo)


def test_rechaza_readiness_no_apto(tmp_path: Path):
    origen = tmp_path / "origen.db"
    backup = tmp_path / "backup.db"
    readiness = tmp_path / "readiness.json"

    _crear_db(origen)
    crear_backup_verificado(origen, backup)
    _readiness(readiness)

    datos = json.loads(readiness.read_text(encoding="utf-8"))
    datos["listo_para_canary"] = False
    readiness.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "
",
        encoding="utf-8",
    )

    resultado = ValidadorEvidenciaCanaryV3().validar(
        readiness,
        backup,
    )

    assert not resultado.apto
    assert any("no está lista" in x for x in resultado.motivos_rechazo)
