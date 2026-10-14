from datetime import date
from decimal import Decimal

from aplicacion.consultas.pago_one_shot_v3 import (
    PagoOneShotV3Query,
    proyectar_one_shot,
)
from aplicacion.puertos.pago_v3_auditable import (
    ImputacionPagoV3Read,
    PagoV3Read,
    ReconciliacionPagoV3Read,
)
from infraestructura.consultas.pagos_v3 import PagoV3Read as PagoV3ReadInfraestructura


def pago_base(imputaciones):
    reconciliacion = ReconciliacionPagoV3Read(
        monto_pago=Decimal("130.00"),
        suma_imputaciones=Decimal("130.00"),
        suma_ledger_pago_debe=Decimal("130.00"),
        suma_ledger_prestamo_haber=Decimal("130.00"),
        suma_distribucion_inversores=Decimal("130.00"),
        hay_distribucion_inversores=True,
    )
    return PagoV3Read(
        pago_id=1, prestamo_id=1, fecha_real="2026-10-07", fecha_valor="2026-10-07",
        monto=Decimal("130.00"), moneda="ARS", tipo_pago="ADELANTO_RAI",
        monto_a_capital=Decimal("130.00"), intereses_ahorrados=Decimal("27.00"),
        cuotas_restantes_antes=4, cuotas_restantes_despues=3, opcion_adelanto="RAI",
        motor_version="V3-G5", plan_hash=None, plan=None,
        imputaciones=tuple(imputaciones), ledger=(), auditoria=(), reconciliacion=reconciliacion,
    )


def test_one_shot_identifica_prepago_por_origen():
    pago = pago_base([
        ImputacionPagoV3Read(1, 1, "INTERES", Decimal("20.00"), "SALDO_CONTRACTUAL", ()),
        ImputacionPagoV3Read(2, 1, "CAPITAL", Decimal("80.00"), "SALDO_CONTRACTUAL", ()),
        ImputacionPagoV3Read(3, None, "CAPITAL", Decimal("30.00"), "PREPAGO", ()),
    ])
    r = proyectar_one_shot(pago)
    assert r.capital_aplicado == Decimal("110.00")
    assert r.prepago == Decimal("30.00")
    assert r.tiene_prepago
    assert r.intereses_ahorrados == Decimal("27.00")


def test_one_shot_es_proyeccion_inmutable_y_no_financiera():
    pago = pago_base([
        ImputacionPagoV3Read(1, 1, "INTERES", Decimal("20.00"), "SALDO_CONTRACTUAL", ()),
        ImputacionPagoV3Read(2, 1, "CAPITAL", Decimal("110.00"), "SALDO_CONTRACTUAL", ()),
    ])
    r = proyectar_one_shot(pago)
    assert r.cantidad_imputaciones == 2
    assert r.motor_version == "V3-G5"


def test_one_shot_mantiene_reconciliacion_del_read_model():
    pago = pago_base([
        ImputacionPagoV3Read(1, 1, "INTERES", Decimal("20.00"), "SALDO_CONTRACTUAL", ()),
        ImputacionPagoV3Read(2, 1, "CAPITAL", Decimal("110.00"), "SALDO_CONTRACTUAL", ()),
    ])
    assert proyectar_one_shot(pago).reconciliado is True


class _ConsultaPagoV3Falsa:
    """Lector falso del contrato público; la prueba no abre SQLite."""

    def __init__(self, pago):
        self._pago = pago

    def obtener_pago_v3(self, pago_id):
        assert pago_id == self._pago.pago_id
        return self._pago


def test_one_shot_consulta_el_pago_por_contrato_sin_sqlite():
    pago = pago_base([
        ImputacionPagoV3Read(1, 1, "INTERES", Decimal("20.00"), "SALDO_CONTRACTUAL", ()),
        ImputacionPagoV3Read(2, 1, "CAPITAL", Decimal("80.00"), "SALDO_CONTRACTUAL", ()),
        ImputacionPagoV3Read(3, None, "CAPITAL", Decimal("30.00"), "PREPAGO", ()),
    ])

    resultado = PagoOneShotV3Query(_ConsultaPagoV3Falsa(pago)).obtener(1)

    assert resultado.pago_id == 1
    assert resultado.capital_aplicado == Decimal("110.00")
    assert resultado.prepago == Decimal("30.00")
    assert resultado.reconciliado is True


def test_dtos_publicos_conservan_las_rutas_de_importacion_historicas():
    assert PagoV3ReadInfraestructura is PagoV3Read
