"""Pruebas unitarias para el aplicador de adelantos Legacy."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from aplicacion.servicios import aplicador_adelanto_legacy as modulo
from aplicacion.servicios.aplicador_adelanto_legacy import AplicadorAdelantoLegacy


class PrestamosFalsos:
    def __init__(self, *, cuotas, tasa={"tasa_anual": Decimal("0.30"), "modalidad": "TNA"}):
        self._cuotas = cuotas
        self._tasa = tasa
        self.version_consultada = None
        self.eliminaciones = []
        self.cuotas_creadas = []

    def version_activa(self, prestamo_id):
        return 9

    def info_tasa_activa(self, prestamo_id):
        return self._tasa

    def cuotas(self, version_id):
        self.version_consultada = version_id
        return self._cuotas

    def borrar_cuotas_pendientes_desde(self, version_id, numero_inicio):
        self.eliminaciones.append((version_id, numero_inicio))

    def crear_cuota_individual(self, **kwargs):
        self.cuotas_creadas.append(kwargs)
        return len(self.cuotas_creadas)


class PagosFalsos:
    def __init__(self):
        self.actualizaciones = []

    def actualizar_datos_adelanto(self, **kwargs):
        self.actualizaciones.append(kwargs)


class RecalculosFalsos:
    def __init__(self):
        self.registros = []

    def registrar(self, **kwargs):
        self.registros.append(kwargs)
        return len(self.registros)


def _cuota(identificador, numero, *, estado="PENDIENTE", saldo="1000.00",
           interes="10.00", fecha_vencimiento=None, cuota="100.00"):
    return SimpleNamespace(
        id=identificador,
        numero=numero,
        estado=estado,
        saldo=Decimal(saldo),
        interes=Decimal(interes),
        cuota=Decimal(cuota),
        fecha_vencimiento=fecha_vencimiento or date(2026, numero, 1),
    )


def _fila(interes: str, numero: int):
    return {
        "vencimiento": date(2026, numero, 1),
        "capital_inicial": Decimal("500.00"),
        "interes": Decimal(interes),
        "capital": Decimal("500.00") - Decimal(interes),
        "cuota": Decimal("500.00"),
        "saldo": Decimal("0.00"),
    }


_TASA_POR_DEFECTO = object()


def _crear_aplicador(cuotas, *, tasa=_TASA_POR_DEFECTO):
    if tasa is _TASA_POR_DEFECTO:
        tasa = {"tasa_anual": Decimal("0.30"), "modalidad": "TNA"}
    prestamos = PrestamosFalsos(cuotas=cuotas, tasa=tasa)
    pagos = PagosFalsos()
    recalculos = RecalculosFalsos()
    aplicador = AplicadorAdelantoLegacy(
        prestamos=prestamos,
        pagos=pagos,
        recalculos=recalculos,
    )
    return aplicador, prestamos, pagos, recalculos


def test_rai_reemplaza_solo_cuotas_futuras_y_registra_el_ahorro(monkeypatch):
    objetivo = _cuota(2, 2, saldo="800.00", interes="0.00")
    futura_1 = _cuota(3, 3, interes="30.00")
    futura_2 = _cuota(4, 4, interes="20.00")
    cerrada_antes = _cuota(1, 1, estado="PAGADA", interes="0.00")
    tabla = [_fila("25.00", 3), _fila("10.00", 4)]
    llamadas = []

    def recalcular(**kwargs):
        llamadas.append(kwargs)
        return tabla

    monkeypatch.setattr(modulo, "recalcular_rai", recalcular)
    aplicador, prestamos, pagos, recalculos = _crear_aplicador(
        [cerrada_antes, objetivo, futura_1, futura_2]
    )

    aplicador.aplicar(
        prestamo_id=7,
        pago_id=55,
        cuota_objetivo=objetivo,
        monto_adelanto=Decimal("200.00"),
        opcion="RAI",
        fecha=date(2026, 2, 15),
    )

    assert len(llamadas) == 1
    assert llamadas[0]["capital_pendiente"] == Decimal("600.00")
    assert llamadas[0]["meses_restantes"] == 2
    assert llamadas[0]["fecha_ultimo_vencimiento"] == futura_2.fecha_vencimiento
    assert prestamos.version_consultada == 9
    assert prestamos.eliminaciones == [(9, 3)]
    assert [fila["numero"] for fila in prestamos.cuotas_creadas] == [3, 4]
    assert all(fila["fue_recalculada"] is True for fila in prestamos.cuotas_creadas)
    assert pagos.actualizaciones == [{
        "pago_id": 55,
        "intereses_ahorrados": Decimal("15.00"),
        "cuotas_restantes_despues": 2,
        "opcion_adelanto": "RAI",
    }]
    assert len(recalculos.registros) == 1
    registro = recalculos.registros[0]
    assert registro["tipo"] == "RAI"
    assert registro["capital_antes"] == Decimal("800.00")
    assert registro["capital_despues"] == Decimal("600.00")
    assert registro["intereses_antes"] == Decimal("50.00")
    assert registro["intereses_despues"] == Decimal("35.00")
    assert registro["cuota_objetivo_numero"] == 2
    assert '"interes": "25.00"' in registro["detalle_json"]


def test_rni_si_el_calculo_no_entrega_cronograma_no_escribe(monkeypatch):
    objetivo = _cuota(2, 2, saldo="800.00", interes="0.00")
    futura = _cuota(3, 3, interes="30.00")
    monkeypatch.setattr(modulo, "recalcular_rni", lambda **kwargs: (None, 0))
    aplicador, prestamos, pagos, recalculos = _crear_aplicador([objetivo, futura])

    aplicador.aplicar(
        prestamo_id=7,
        pago_id=55,
        cuota_objetivo=objetivo,
        monto_adelanto=Decimal("200.00"),
        opcion="RNI",
        fecha=date(2026, 2, 15),
    )

    assert prestamos.eliminaciones == []
    assert prestamos.cuotas_creadas == []
    assert pagos.actualizaciones == []
    assert recalculos.registros == []


@pytest.mark.parametrize(
    "cuotas,tasa",
    [
        ([_cuota(2, 2)], None),
        ([_cuota(2, 2, estado="PAGADA")], {
            "tasa_anual": Decimal("0.30"), "modalidad": "TNA"
        }),
    ],
)
def test_sin_tasa_o_sin_cuotas_futuras_no_modifica_datos(cuotas, tasa):
    aplicador, prestamos, pagos, recalculos = _crear_aplicador(cuotas, tasa=tasa)

    aplicador.aplicar(
        prestamo_id=7,
        pago_id=55,
        cuota_objetivo=_cuota(2, 2),
        monto_adelanto=Decimal("200.00"),
        opcion="RAI",
        fecha=date(2026, 2, 15),
    )

    assert prestamos.eliminaciones == []
    assert prestamos.cuotas_creadas == []
    assert pagos.actualizaciones == []
    assert recalculos.registros == []
