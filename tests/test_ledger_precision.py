"""Pruebas de exactitud monetaria del ledger."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios.ledger import LedgerRepo


@pytest.fixture
def ledger(tmp_path: Path):
    """Crea una base temporal con el schema completo y devuelve el ledger."""
    ruta = tmp_path / "ledger_precision.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        yield LedgerRepo(db)


def test_saldo_suma_importes_decimal_sin_perdida_precision(ledger):
    """0,10 + 0,20 - 0,30 debe ser exactamente 0,00."""
    fecha = date(2026, 10, 4)
    ledger.registrar_movimiento(
        "PRESTAMO", 1, "PRUEBA", Decimal("0.10"), Decimal("0"), fecha, "prec-1"
    )
    ledger.registrar_movimiento(
        "PRESTAMO", 1, "PRUEBA", Decimal("0.20"), Decimal("0"), fecha, "prec-2"
    )
    ledger.registrar_movimiento(
        "PRESTAMO", 1, "PRUEBA", Decimal("0"), Decimal("0.30"), fecha, "prec-3"
    )

    assert ledger.saldo("PRESTAMO", 1) == Decimal("0.00")


def test_verificar_cuadre_usa_decimal_exactamente(ledger):
    """Un ledger 0,10 + 0,20 = 0,30 debe cuadrar exactamente."""
    fecha = date(2026, 10, 4)
    ledger.registrar_movimiento(
        "PRESTAMO", 1, "PRUEBA", Decimal("0.10"), Decimal("0"), fecha, "cuadre-1"
    )
    ledger.registrar_movimiento(
        "PRESTAMO", 1, "PRUEBA", Decimal("0.20"), Decimal("0"), fecha, "cuadre-2"
    )
    ledger.registrar_movimiento(
        "PRESTAMO", 1, "PRUEBA", Decimal("0"), Decimal("0.30"), fecha, "cuadre-3"
    )

    assert ledger.verificar_cuadre() is True


def test_saldo_respeta_fecha_de_corte(ledger):
    """El saldo histórico excluye movimientos posteriores a la fecha solicitada."""
    ledger.registrar_movimiento(
        "PRESTAMO",
        1,
        "PRUEBA",
        Decimal("100.10"),
        Decimal("0"),
        date(2026, 10, 1),
        "fecha-1",
    )
    ledger.registrar_movimiento(
        "PRESTAMO",
        1,
        "PRUEBA",
        Decimal("50.20"),
        Decimal("0"),
        date(2026, 10, 5),
        "fecha-2",
    )

    assert ledger.saldo("PRESTAMO", 1, hasta=date(2026, 10, 1)) == Decimal("100.10")
    assert ledger.saldo("PRESTAMO", 1, hasta=date(2026, 10, 5)) == Decimal("150.30")
