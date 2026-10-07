"""Tests del feature flag de V3 protegido por preflight."""
from dataclasses import replace
from decimal import Decimal

import pytest

from aplicacion.servicios.feature_flag_motor_pago_v3 import (
    FeatureFlagMotorPagoV3,
)
from aplicacion.servicios.puente_motor_pago_v3 import ModoMotorPagoV3
from aplicacion.servicios.preflight_motor_pago_v3 import (
    CriterioPreflightV3,
    ResultadoPreflightV3,
)
from dominio.excepciones import ErrorValidacion


def preflight(apto: bool) -> ResultadoPreflightV3:
    return ResultadoPreflightV3(
        apto=apto,
        criterios=(
            CriterioPreflightV3(
                "test",
                apto,
                "preflight de prueba",
            ),
        ),
    )


def test_sin_configuracion_mantiene_legacy():
    decision = FeatureFlagMotorPagoV3().resolver(solicitado=None)

    assert decision.modo is ModoMotorPagoV3.LEGACY
    assert decision.solicitado is ModoMotorPagoV3.LEGACY


def test_legacy_explicito_es_permitido():
    decision = FeatureFlagMotorPagoV3().resolver(
        solicitado=ModoMotorPagoV3.LEGACY,
    )

    assert decision.modo is ModoMotorPagoV3.LEGACY
    assert decision.preflight_apto is False


def test_sombra_explicito_es_permitido():
    decision = FeatureFlagMotorPagoV3().resolver(
        solicitado="SOMBRA",
        preflight=preflight(False),
    )

    assert decision.modo is ModoMotorPagoV3.SOMBRA
    assert decision.preflight_apto is False


def test_v3_sin_preflight_es_rechazado():
    with pytest.raises(
        ErrorValidacion,
        match="sin resultado de preflight",
    ):
        FeatureFlagMotorPagoV3().resolver(
            solicitado=ModoMotorPagoV3.V3,
        )


def test_v3_con_preflight_no_apto_es_rechazado():
    with pytest.raises(
        ErrorValidacion,
        match="preflight no está aprobado",
    ):
        FeatureFlagMotorPagoV3().resolver(
            solicitado="V3",
            preflight=preflight(False),
        )


def test_v3_con_preflight_apto_es_habilitado():
    decision = FeatureFlagMotorPagoV3().resolver(
        solicitado="V3",
        preflight=preflight(True),
    )

    assert decision.modo is ModoMotorPagoV3.V3
    assert decision.preflight_apto is True
    assert "aprobado" in decision.motivo


def test_modo_invalido_es_error_explicitamente():
    with pytest.raises(ErrorValidacion, match="inválido"):
        FeatureFlagMotorPagoV3().resolver(
            solicitado="NO_EXISTE",
            preflight=preflight(True),
        )


def test_preflight_apto_no_es_ignorado_para_legacy():
    decision = FeatureFlagMotorPagoV3().resolver(
        solicitado="LEGACY",
        preflight=preflight(True),
    )

    assert decision.modo is ModoMotorPagoV3.LEGACY
    assert decision.preflight_apto is True
