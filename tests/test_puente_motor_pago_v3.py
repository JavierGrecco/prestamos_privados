from datetime import date
from decimal import Decimal

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.puente_motor_pago_v3 import (
    ModoMotorPagoV3,
    PuenteMotorPagoV3,
)
from dominio.excepciones import ErrorValidacion


def command():
    return RegistrarPagoCommand(
        prestamo_id=1,
        monto=Decimal("100.00"),
        fecha_real=date(2026, 10, 7),
        usuario="tester",
    )


def test_legacy_es_el_motor_efectivo_en_modo_legacy():
    llamadas = []
    puente = PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.LEGACY,
        registrar_legacy=lambda c: llamadas.append("legacy") or "ok-legacy",
    )
    r = puente.ejecutar(command())
    assert r.resultado_efectivo == "ok-legacy"
    assert r.plan_sombra_v3 is None
    assert llamadas == ["legacy"]


def test_v3_es_el_motor_efectivo_en_modo_v3():
    llamadas = []
    puente = PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.V3,
        registrar_v3=lambda c: llamadas.append("v3") or "ok-v3",
    )
    r = puente.ejecutar(command())
    assert r.resultado_efectivo == "ok-v3"
    assert llamadas == ["v3"]


def test_sombra_ejecuta_legacy_y_v3_sin_hacer_v3_efectivo():
    llamadas = []
    puente = PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.SOMBRA,
        registrar_legacy=lambda c: llamadas.append("legacy") or {"legacy": 1},
        capturar_snapshot=lambda c: llamadas.append("snapshot") or {"estado": "inicial"},
        planificar_v3_sombra=lambda c, snapshot: llamadas.append(("v3-shadow", snapshot)) or {"v3": 1},
        comparar_sombra=lambda legacy, v3: None,
    )
    r = puente.ejecutar(command())
    assert r.resultado_efectivo == {"legacy": 1}
    assert r.plan_sombra_v3 == {"v3": 1}
    assert r.divergencia is None
    assert llamadas == ["snapshot", "legacy", ("v3-shadow", {"estado": "inicial"})]


def test_sombra_emite_divergencia_y_la_observa():
    observadas = []
    puente = PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.SOMBRA,
        registrar_legacy=lambda c: {"legacy": 1},
        capturar_snapshot=lambda c: {"estado": "inicial"},
        planificar_v3_sombra=lambda c, snapshot: {"v3": 2},
        comparar_sombra=lambda legacy, v3: "monto aplicado diferente",
        observar_divergencia=observadas.append,
    )
    r = puente.ejecutar(command())
    assert r.divergencia is not None
    assert r.divergencia.resumen == "monto aplicado diferente"
    assert len(observadas) == 1
    assert observadas[0] == r.divergencia
    assert len(r.divergencia.fingerprint) == 64


def test_sombra_no_llama_registrador_v3_persistente():
    persistentes = []
    puente = PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.SOMBRA,
        registrar_legacy=lambda c: "legacy",
        registrar_v3=lambda c: persistentes.append("NO-DEBE") or "v3",
        capturar_snapshot=lambda c: "snapshot",
        planificar_v3_sombra=lambda c, snapshot: "plan",
        comparar_sombra=lambda legacy, v3: None,
    )
    r = puente.ejecutar(command())
    assert r.resultado_efectivo == "legacy"
    assert persistentes == []


def test_configuracion_invalida_sin_legacy():
    with pytest.raises(ErrorValidacion, match="registrador legacy"):
        PuenteMotorPagoV3(modo=ModoMotorPagoV3.LEGACY)


def test_configuracion_invalida_sin_planificador_sombra():
    with pytest.raises(ErrorValidacion, match="planificador V3"):
        PuenteMotorPagoV3(
            modo=ModoMotorPagoV3.SOMBRA,
            registrar_legacy=lambda c: "legacy",
            capturar_snapshot=lambda c: "snapshot",
            comparar_sombra=lambda legacy, v3: None,
        )


def test_sombra_convierte_falla_del_planificador_en_incidente_no_bloqueante():
    puente = PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.SOMBRA,
        registrar_legacy=lambda c: "legacy-ok",
        capturar_snapshot=lambda c: "snapshot",
        planificar_v3_sombra=lambda c, snapshot: (_ for _ in ()).throw(
            RuntimeError("fallo sombra")
        ),
        comparar_sombra=lambda *_: None,
    )

    resultado = puente.ejecutar(command())

    assert resultado.resultado_efectivo == "legacy-ok"
    assert resultado.plan_sombra_v3 is None
    assert resultado.divergencia is None
    assert resultado.error_sombra == "RuntimeError: fallo sombra"


def test_sombra_convierte_falla_del_comparador_en_incidente_no_bloqueante():
    puente = PuenteMotorPagoV3(
        modo=ModoMotorPagoV3.SOMBRA,
        registrar_legacy=lambda c: "legacy-ok",
        capturar_snapshot=lambda c: "snapshot",
        planificar_v3_sombra=lambda c, snapshot: "plan-ok",
        comparar_sombra=lambda *_: (_ for _ in ()).throw(
            RuntimeError("fallo comparador")
        ),
    )

    resultado = puente.ejecutar(command())

    assert resultado.resultado_efectivo == "legacy-ok"
    assert resultado.plan_sombra_v3 == "plan-ok"
    assert resultado.error_sombra == "RuntimeError: fallo comparador"


def test_configuracion_invalida_sombra_sin_snapshot():
    with pytest.raises(ErrorValidacion, match="capturador de snapshot"):
        PuenteMotorPagoV3(
            modo=ModoMotorPagoV3.SOMBRA,
            registrar_legacy=lambda c: "legacy",
            planificar_v3_sombra=lambda c, snapshot: "plan",
            comparar_sombra=lambda *_: None,
        )
