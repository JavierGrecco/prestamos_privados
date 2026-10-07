from datetime import date
from decimal import Decimal

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.registro_pago_v3 import (
    EstadoRegistroPagoV3,
    IdempotenciaPagoV3,
    RegistrarPagoV3,
    fingerprint_command,
)
from dominio.excepciones import ErrorInvariante


class PlanFalso:
    def __init__(self, marker):
        self.marker = marker


class RepoFalso:
    def __init__(self, *, revision=7, obligaciones=("O1", "O2")):
        self.estado = EstadoRegistroPagoV3(10, revision, obligaciones)
        self.idempotencia = {}
        self.begin_count = 0
        self.commit_count = 0
        self.rollback_count = 0
        self.persisted = []
        self.next_pago_id = 100

    def begin(self):
        self.begin_count += 1

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1

    def buscar_idempotencia(self, key):
        return self.idempotencia.get(key)

    def obtener_estado_pago(self, prestamo_id):
        return self.estado

    def persistir_pago(self, command, plan, *, fingerprint, revision_esperada):
        self.persisted.append((command, plan, fingerprint, revision_esperada))
        return self.next_pago_id


def command(**changes):
    data = dict(
        prestamo_id=10,
        monto=Decimal("100.00"),
        fecha_real=date(2026, 10, 7),
        usuario="admin",
    )
    data.update(changes)
    return RegistrarPagoCommand(**data)


def test_fingerprint_es_estable_y_no_incluye_la_clave_de_idempotencia():
    a = command(idempotency_key="k1")
    b = command(idempotency_key="k2")
    assert fingerprint_command(a) == fingerprint_command(b)


def test_ejecuta_relectura_plan_persistencia_y_commit():
    repo = RepoFalso(revision=12)
    llamadas = []

    def calcular_plan(**kwargs):
        llamadas.append(kwargs)
        return PlanFalso("plan-vigente")

    resultado = RegistrarPagoV3(repo, calcular_plan).ejecutar(command())

    assert resultado.pago_id == 100
    assert resultado.revision_utilizada == 12
    assert resultado.es_repeticion_idempotente is False
    assert resultado.plan.marker == "plan-vigente"
    assert llamadas[0]["revision_prestamo"] == 12
    assert llamadas[0]["obligaciones"] == ("O1", "O2")
    assert repo.persisted[0][3] == 12
    assert repo.begin_count == 1
    assert repo.commit_count == 1
    assert repo.rollback_count == 0


def test_revision_explicita_debe_coincidir_con_estado_releido():
    repo = RepoFalso(revision=12)
    with pytest.raises(ErrorInvariante, match="Conflicto de revisión"):
        RegistrarPagoV3(repo, lambda **_: PlanFalso("x")).ejecutar(
            command(revision_prestamo=11)
        )
    assert repo.persisted == []
    assert repo.commit_count == 0
    assert repo.rollback_count == 1


def test_error_de_calculo_hace_rollback_y_no_persistencia():
    repo = RepoFalso()

    def calcular_plan(**_):
        raise ErrorInvariante("plan inválido")

    with pytest.raises(ErrorInvariante, match="plan inválido"):
        RegistrarPagoV3(repo, calcular_plan).ejecutar(command())

    assert repo.persisted == []
    assert repo.commit_count == 0
    assert repo.rollback_count == 1


def test_error_de_persistencia_hace_rollback():
    class RepoQueFalla(RepoFalso):
        def persistir_pago(self, *args, **kwargs):
            raise RuntimeError("falló DB")

    repo = RepoQueFalla()
    with pytest.raises(RuntimeError, match="falló DB"):
        RegistrarPagoV3(repo, lambda **_: PlanFalso("x")).ejecutar(command())

    assert repo.commit_count == 0
    assert repo.rollback_count == 1


def test_repeticion_idempotente_no_vuelve_a_calcular_ni_persistir():
    base = command(idempotency_key="pago-123")
    repo = RepoFalso(revision=22)
    fp = fingerprint_command(base)
    repo.idempotencia["pago-123"] = IdempotenciaPagoV3("pago-123", fp, 900)

    llamadas = []
    resultado = RegistrarPagoV3(
        repo,
        lambda **kwargs: llamadas.append(kwargs) or PlanFalso("NO-DEBERIA")
    ).ejecutar(base)

    assert resultado.pago_id == 900
    assert resultado.es_repeticion_idempotente is True
    assert resultado.revision_utilizada is None
    assert resultado.plan is None
    assert llamadas == []
    assert repo.persisted == []
    assert repo.commit_count == 1
    assert repo.rollback_count == 0


def test_misma_clave_con_payload_diferente_es_error():
    base = command(idempotency_key="pago-123")
    diferente = command(idempotency_key="pago-123", monto=Decimal("101.00"))
    repo = RepoFalso()
    repo.idempotencia["pago-123"] = IdempotenciaPagoV3(
        "pago-123", fingerprint_command(base), 900
    )

    with pytest.raises(ErrorInvariante, match="payload diferente"):
        RegistrarPagoV3(repo, lambda **_: PlanFalso("NO")).ejecutar(diferente)

    assert repo.persisted == []
    assert repo.commit_count == 0
    assert repo.rollback_count == 1


def test_se_pasa_el_fingerprint_y_revision_a_persistencia():
    repo = RepoFalso(revision=31)
    c = command(idempotency_key="idem-31")
    RegistrarPagoV3(repo, lambda **_: PlanFalso("x")).ejecutar(c)

    _, _, fp, rev = repo.persisted[0]
    assert fp == fingerprint_command(c)
    assert rev == 31
