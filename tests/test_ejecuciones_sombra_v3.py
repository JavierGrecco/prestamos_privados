"""Tests for the append-only SOMBRA execution repository and bridge."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.puente_motor_pago_v3 import (
    EjecucionSombraMotorPagoV3,
    ModoMotorPagoV3,
    PuenteMotorPagoV3,
    ResultadoEjecucionSombraV3,
)
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios.ejecuciones_sombra_v3 import (
    EjecucionesSombraV3Repo,
)


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "ejecuciones_sombra.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield db


def _ejecucion(resultado: ResultadoEjecucionSombraV3, fingerprint: str):
    return EjecucionSombraMotorPagoV3(
        fingerprint=fingerprint,
        prestamo_id=1,
        pago_legacy_id=10,
        resultado=resultado,
        revision_snapshot=3,
        resumen=None if resultado is ResultadoEjecucionSombraV3.SIN_DIVERGENCIA else "detalle",
    )


def test_repo_persiste_los_tres_resultados_y_permite_consulta(db):
    repo = EjecucionesSombraV3Repo(db)

    for i, resultado in enumerate(
        (
            ResultadoEjecucionSombraV3.SIN_DIVERGENCIA,
            ResultadoEjecucionSombraV3.DIVERGENCIA,
            ResultadoEjecucionSombraV3.ERROR_SOMBRA,
        ),
        start=1,
    ):
        repo.registrar(_ejecucion(resultado, f"fp-{i}"))

    filas = repo.por_prestamo(1)
    assert [f["resultado"] for f in filas] == [
        "SIN_DIVERGENCIA",
        "DIVERGENCIA",
        "ERROR_SOMBRA",
    ]
    assert repo.por_resultado("SIN_DIVERGENCIA")[0]["fingerprint"] == "fp-1"
    assert repo.por_fingerprint("fp-3")[0]["resultado"] == "ERROR_SOMBRA"


def test_repo_es_append_only(db):
    repo = EjecucionesSombraV3Repo(db)
    repo.registrar(
        _ejecucion(ResultadoEjecucionSombraV3.SIN_DIVERGENCIA, "fp")
    )

    with pytest.raises(Exception, match="inmutables"):
        db.ejecutar(
            "UPDATE ejecuciones_sombra_v3 SET resumen=? WHERE id=?",
            ("cambio", 1),
        )

    with pytest.raises(Exception, match="no se eliminan"):
        db.ejecutar(
            "DELETE FROM ejecuciones_sombra_v3 WHERE id=?",
            (1,),
        )


def test_puente_informa_resultado_sin_divergencia_y_snapshot(db):
    eventos = []

    puente = PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.SOMBRA,
        registrar_legacy=lambda _: 10,
        capturar_snapshot=lambda _: SimpleNamespace(revision_prestamo=3),
        planificar_v3_sombra=lambda _, snapshot: snapshot,
        comparar_sombra=lambda *_: None,
        observar_ejecucion=eventos.append,
    )

    command = RegistrarPagoCommand(
        prestamo_id=1,
        monto=Decimal("100.00"),
        fecha_real=date(2026, 10, 7),
        usuario="i5",
    )

    resultado = puente.ejecutar(command)

    assert resultado.ejecucion_sombra is not None
    assert resultado.ejecucion_sombra.resultado is ResultadoEjecucionSombraV3.SIN_DIVERGENCIA
    assert resultado.ejecucion_sombra.revision_snapshot == 3
    assert eventos == [resultado.ejecucion_sombra]


def test_observador_de_ejecucion_no_bloquea_el_resultado_legacy(db):
    def falla(_):
        raise RuntimeError("storage de ejecuciones fuera de servicio")

    puente = PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.SOMBRA,
        registrar_legacy=lambda _: 10,
        capturar_snapshot=lambda _: SimpleNamespace(revision_prestamo=1),
        planificar_v3_sombra=lambda _, snapshot: snapshot,
        comparar_sombra=lambda *_: None,
        observar_ejecucion=falla,
    )

    command = RegistrarPagoCommand(
        prestamo_id=1,
        monto=Decimal("100.00"),
        fecha_real=date(2026, 10, 7),
        usuario="i5",
    )

    resultado = puente.ejecutar(command)

    assert resultado.resultado_efectivo == 10
    assert resultado.ejecucion_sombra is not None
    assert resultado.error_observabilidad == (
        "RuntimeError: storage de ejecuciones fuera de servicio"
    )
