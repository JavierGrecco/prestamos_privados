from datetime import date, datetime
from decimal import Decimal

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from dominio.excepciones import ErrorValidacion


def command(**overrides):
    data = {
        "prestamo_id": 10,
        "monto": Decimal("50000.007"),
        "fecha_real": date(2026, 10, 7),
        "usuario": " admin ",
    }
    data.update(overrides)
    return RegistrarPagoCommand(**data)


def test_normaliza_monto_usuario_y_fecha_valor_por_defecto():
    c = command()
    assert c.monto == Decimal("50000.01")
    assert c.usuario == "admin"
    assert c.fecha_valor == date(2026, 10, 7)


def test_fecha_valor_puede_ser_distinta_de_fecha_real():
    c = command(fecha_valor=date(2026, 10, 6))
    assert c.fecha_real == date(2026, 10, 7)
    assert c.fecha_valor == date(2026, 10, 6)


def test_normaliza_textos_opcionales():
    c = command(
        medio=" TRANSFERENCIA ", referencia=" REF-1 ", nota=" nota ",
        opcion_adelanto=" RAI ", idempotency_key="  pago-123  ",
    )
    assert c.medio == "TRANSFERENCIA"
    assert c.referencia == "REF-1"
    assert c.nota == "nota"
    assert c.opcion_adelanto == "RAI"
    assert c.idempotency_key == "pago-123"


def test_command_es_inmutable():
    c = command()
    with pytest.raises(Exception):
        c.monto = Decimal("1")


def test_rechazos_basicos():
    with pytest.raises(ErrorValidacion):
        command(monto=Decimal("0"))
    with pytest.raises(ErrorValidacion):
        command(prestamo_id=0)
    with pytest.raises(ErrorValidacion):
        command(usuario="   ")
    with pytest.raises(ErrorValidacion):
        command(opcion_adelanto="OTRA")
    with pytest.raises(ErrorValidacion):
        command(idempotency_key="   ")
    with pytest.raises(ErrorValidacion):
        command(idempotency_key="x" * 256)
    with pytest.raises(ErrorValidacion):
        command(revision_prestamo=-1)


def test_command_determinista_para_los_mismos_datos():
    assert command() == command()

@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("fecha_real", datetime(2026, 10, 7, 11, 30)),
        ("fecha_valor", datetime(2026, 10, 7, 12, 0)),
    ],
)
def test_rechaza_datetime_donde_se_requiere_fecha_civil(campo, valor):
    with pytest.raises(ErrorValidacion, match="fecha civil sin hora"):
        command(**{campo: valor})

