"""Tests del preflight objetivo de V3."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.servicios.preflight_motor_pago_v3 import PreflightMotorPagoV3
from aplicacion.servicios.puente_motor_pago_v3 import (
    ResultadoEjecucionSombraV3,
    EjecucionSombraMotorPagoV3,
)
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios.ejecuciones_sombra_v3 import (
    EjecucionesSombraV3Repo,
)


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "preflight.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield db


def _registrar_ejecucion(db, resultado, fingerprint):
    repo = EjecucionesSombraV3Repo(db)
    repo.registrar(
        EjecucionSombraMotorPagoV3(
            fingerprint=fingerprint,
            prestamo_id=1,
            pago_legacy_id=None,
            resultado=resultado,
            revision_snapshot=0,
            resumen=None,
        )
    )


def test_preflight_vacio_no_es_apto(db):
    resultado = PreflightMotorPagoV3(db).evaluar()

    assert resultado.apto is False
    assert len(resultado.criterios) == 6
    assert "Ejecuciones SOMBRA: 0; mínimo: 100" in resultado.motivos_rechazo
    assert resultado.evidencia is not None
    assert resultado.evidencia.ejecuciones_sombra == 0
    assert resultado.evidencia.schema_actual == 14


def test_preflight_puede_ser_apto_con_umbral_controlado(db):
    for i in range(10):
        _registrar_ejecucion(
            db,
            ResultadoEjecucionSombraV3.SIN_DIVERGENCIA,
            f"fp-{i}",
        )

    resultado = PreflightMotorPagoV3(
        db,
        ejecuciones_minimas=10,
    ).evaluar()

    assert resultado.apto is True
    assert resultado.motivos_rechazo == ()
    assert resultado.criterios[0].nombre == "schema"
    assert resultado.criterios[1].nombre == "integridad_v3"


def test_preflight_rechaza_divergencias_y_errores(db):
    for i in range(10):
        _registrar_ejecucion(
            db,
            ResultadoEjecucionSombraV3.SIN_DIVERGENCIA,
            f"ok-{i}",
        )
    _registrar_ejecucion(
        db,
        ResultadoEjecucionSombraV3.DIVERGENCIA,
        "divergencia-1",
    )
    _registrar_ejecucion(
        db,
        ResultadoEjecucionSombraV3.ERROR_SOMBRA,
        "error-1",
    )

    resultado = PreflightMotorPagoV3(
        db,
        ejecuciones_minimas=10,
        divergencias_maximas=0,
        errores_maximos=0,
    ).evaluar()

    assert resultado.apto is False
    assert any("Divergencias: 1" in x for x in resultado.motivos_rechazo)
    assert any("Errores SOMBRA: 1" in x for x in resultado.motivos_rechazo)
    assert abs(
        db.consultar_uno(
            "SELECT COUNT(*) AS n FROM ejecuciones_sombra_v3"
        )["n"]
        - 12
    ) == 0


def test_preflight_rechaza_umbral_de_coincidencia(db):
    for i in range(8):
        _registrar_ejecucion(
            db,
            ResultadoEjecucionSombraV3.SIN_DIVERGENCIA,
            f"ok-{i}",
        )
    _registrar_ejecucion(
        db,
        ResultadoEjecucionSombraV3.DIVERGENCIA,
        "div-1",
    )
    _registrar_ejecucion(
        db,
        ResultadoEjecucionSombraV3.DIVERGENCIA,
        "div-2",
    )

    resultado = PreflightMotorPagoV3(
        db,
        ejecuciones_minimas=10,
        divergencias_maximas=2,
        errores_maximos=0,
        tasa_coincidencia_minima=Decimal("0.9"),
    ).evaluar()

    assert resultado.apto is False
    assert any("Tasa de coincidencia" in x for x in resultado.motivos_rechazo)


def test_preflight_rechaza_parametros_invalidos(db):
    with pytest.raises(ValueError):
        PreflightMotorPagoV3(db, version_minima=0)

    with pytest.raises(ValueError):
        PreflightMotorPagoV3(db, tasa_coincidencia_minima=Decimal("1.1"))

    with pytest.raises(ValueError):
        PreflightMotorPagoV3(db, divergencias_maximas=-1)
