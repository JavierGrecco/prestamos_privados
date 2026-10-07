"""Tests del contrato de SOMBRA sobre snapshot previo a Legacy."""
from datetime import date
from decimal import Decimal

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.ejecutor_sombra_pago_v3 import EjecutorSombraPagoV3


def comando():
    return RegistrarPagoCommand(
        prestamo_id=1,
        monto=Decimal("100.00"),
        fecha_real=date(2026, 10, 7),
        fecha_valor=date(2026, 10, 7),
        usuario="tester",
        idempotency_key="I1-SOMBRA",
    )


def test_snapshot_se_toma_antes_de_legacy_y_v3_lo_recibe():
    eventos = []

    def capturar(_):
        eventos.append("snapshot")
        return {"saldo": Decimal("100.00")}

    def legacy(_):
        eventos.append("legacy")
        # Simula mutación que no debe alterar el snapshot.
        return {"saldo": Decimal("80.00")}

    def sombra(_, snapshot):
        eventos.append(("sombra", snapshot["saldo"]))
        assert snapshot["saldo"] == Decimal("100.00")
        return {"saldo_final": Decimal("80.00")}

    def comparar(legacy_result, v3_plan):
        eventos.append(("comparar", legacy_result["saldo"], v3_plan["saldo_final"]))
        return None

    resultado = EjecutorSombraPagoV3(
        capturar_snapshot=capturar,
        ejecutar_legacy=legacy,
        planificar_v3=sombra,
        comparar=comparar,
    ).ejecutar(comando())

    assert eventos == [
        "snapshot",
        "legacy",
        ("sombra", Decimal("100.00")),
        ("comparar", Decimal("80.00"), Decimal("80.00")),
    ]
    assert resultado.divergencia is None
    assert resultado.error_sombra is None
    assert resultado.plan_v3 == {"saldo_final": Decimal("80.00")}
    assert resultado.snapshot_inicial == {"saldo": Decimal("100.00")}
    assert len(resultado.fingerprint) == 64


def test_error_de_v3_sombra_no_invalida_legacy():
    eventos = []

    resultado = EjecutorSombraPagoV3(
        capturar_snapshot=lambda _: {"estado": "inicial"},
        ejecutar_legacy=lambda _: eventos.append("legacy") or "OK",
        planificar_v3=lambda *_: (_ for _ in ()).throw(
            RuntimeError("fallo sombra controlado")
        ),
        comparar=lambda *_: None,
    ).ejecutar(comando())

    assert resultado.resultado_legacy == "OK"
    assert resultado.error_sombra == "RuntimeError: fallo sombra controlado"
    assert resultado.plan_v3 is None
    assert eventos == ["legacy"]


def test_error_del_comparador_no_invalida_legacy():
    resultado = EjecutorSombraPagoV3(
        capturar_snapshot=lambda _: {"estado": "inicial"},
        ejecutar_legacy=lambda _: "OK",
        planificar_v3=lambda *_: "PLAN",
        comparar=lambda *_: (_ for _ in ()).throw(
            ValueError("comparador no disponible")
        ),
    ).ejecutar(comando())

    assert resultado.resultado_legacy == "OK"
    assert resultado.plan_v3 == "PLAN"
    assert resultado.error_sombra == "ValueError: comparador no disponible"


def test_divergencia_se_devuelve_sin_convertirse_en_error():
    resultado = EjecutorSombraPagoV3(
        capturar_snapshot=lambda _: {"saldo": Decimal("100.00")},
        ejecutar_legacy=lambda _: {"saldo": Decimal("90.00")},
        planificar_v3=lambda *_: {"saldo": Decimal("91.00")},
        comparar=lambda *_: "saldo diferente",
    ).ejecutar(comando())

    assert resultado.error_sombra is None
    assert resultado.divergencia == "saldo diferente"


def test_la_sombra_no_acepta_un_snapshot_vacio_por_accidente():
    """El capturador forma parte del contrato; no se inventa estado en la sombra."""
    resultado = EjecutorSombraPagoV3(
        capturar_snapshot=lambda _: None,
        ejecutar_legacy=lambda _: "OK",
        planificar_v3=lambda _, snapshot: (
            None if snapshot is not None else (_ for _ in ()).throw(
                AssertionError("faltó snapshot")
            )
        ),
        comparar=lambda *_: None,
    ).ejecutar(comando())

    assert resultado.error_sombra == "AssertionError: faltó snapshot"
