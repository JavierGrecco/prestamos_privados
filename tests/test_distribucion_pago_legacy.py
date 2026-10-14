"""Pruebas unitarias de la distribución de pagos Legacy a inversores."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from aplicacion.servicios.distribucion_pago_legacy import DistribuidorPagoLegacy


class ParticipacionesFalsas:
    def __init__(self, partes):
        self.partes = partes
        self.prestamo_solicitado = None

    def por_prestamo(self, prestamo_id):
        self.prestamo_solicitado = prestamo_id
        return self.partes


class LedgerFalso:
    def __init__(self):
        self.operaciones = []

    def registrar_operacion(self, *, movimientos, correlacion_id):
        self.operaciones.append({
            "movimientos": movimientos,
            "correlacion_id": correlacion_id,
        })


def _parte(inversor_id: int, porcentaje: str):
    return SimpleNamespace(
        inversor_id=inversor_id,
        porcentaje=Decimal(porcentaje),
    )


def test_distribuye_el_importe_aplicado_segun_la_participacion():
    participaciones = ParticipacionesFalsas([
        _parte(101, "0.40"),
        _parte(202, "0.60"),
    ])
    ledger = LedgerFalso()
    distribuidor = DistribuidorPagoLegacy(
        participaciones=participaciones,
        ledger=ledger,
    )
    fecha = date(2026, 3, 1)

    distribuidor.distribuir(
        prestamo_id=7,
        aplicado={
            "MORA": Decimal("10.00"),
            "INTERES": Decimal("20.00"),
            "CAPITAL": Decimal("70.00"),
        },
        fecha_real=fecha,
        correlacion_id="pago-corr-7",
    )

    assert participaciones.prestamo_solicitado == 7
    assert len(ledger.operaciones) == 1
    operacion = ledger.operaciones[0]
    assert operacion["correlacion_id"] == "pago-corr-7"
    assert operacion["movimientos"] == [
        {
            "entidad": "INVERSOR",
            "entidad_id": 101,
            "tipo_movimiento": "COBRO_PAGO",
            "debe": Decimal("40.0000"),
            "haber": Decimal("0"),
            "fecha": fecha,
        },
        {
            "entidad": "PRESTAMO",
            "entidad_id": 7,
            "tipo_movimiento": "DISTRIBUCION_INVERSOR",
            "debe": Decimal("0"),
            "haber": Decimal("40.0000"),
            "fecha": fecha,
        },
        {
            "entidad": "INVERSOR",
            "entidad_id": 202,
            "tipo_movimiento": "COBRO_PAGO",
            "debe": Decimal("60.0000"),
            "haber": Decimal("0"),
            "fecha": fecha,
        },
        {
            "entidad": "PRESTAMO",
            "entidad_id": 7,
            "tipo_movimiento": "DISTRIBUCION_INVERSOR",
            "debe": Decimal("0"),
            "haber": Decimal("60.0000"),
            "fecha": fecha,
        },
    ]


def test_no_registra_movimientos_si_el_prestamo_no_tiene_inversores():
    ledger = LedgerFalso()
    distribuidor = DistribuidorPagoLegacy(
        participaciones=ParticipacionesFalsas([]),
        ledger=ledger,
    )

    distribuidor.distribuir(
        prestamo_id=7,
        aplicado={"CAPITAL": Decimal("100.00")},
        fecha_real=date(2026, 3, 1),
        correlacion_id="pago-sin-inversores",
    )

    assert ledger.operaciones == []


def test_no_registra_movimientos_si_el_importe_aplicado_es_cero():
    ledger = LedgerFalso()
    distribuidor = DistribuidorPagoLegacy(
        participaciones=ParticipacionesFalsas([_parte(101, "1.00")]),
        ledger=ledger,
    )

    distribuidor.distribuir(
        prestamo_id=7,
        aplicado={
            "MORA": Decimal("0.00"),
            "INTERES": Decimal("0.00"),
            "CAPITAL": Decimal("0.00"),
        },
        fecha_real=date(2026, 3, 1),
        correlacion_id="pago-cero",
    )

    assert ledger.operaciones == []
