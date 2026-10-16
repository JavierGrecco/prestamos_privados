"""Pruebas de la consulta consolidada del historial de inversión."""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from aplicacion.consultas.historial_inversion_reposicion import (
    ConsultaHistorialInversionReposicion,
)
from dominio.excepciones import ErrorValidacion
from infraestructura import BaseDatos
from infraestructura.composicion.historial_inversion_reposicion import (
    crear_consulta_historial_inversion_reposicion,
)
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PlanesReposicionRepo


class _FuenteHistorialFalsa:
    def __init__(self):
        self.llamadas = []
        self.flujos = (
            SimpleNamespace(
                id=7,
                fecha_flujo=date(2026, 10, 1),
                tipo_flujo="APORTE_INVERSION",
                moneda="ARS",
                monto_original=Decimal("1500000.00"),
                equivalente_usd=Decimal("1000.00"),
                naturaleza_cotizacion="OBSERVADA",
                fuente_cotizacion="Cotización pública",
                referencia="Entrada de capital",
            ),
        )
        self.valuaciones = (
            SimpleNamespace(
                id=9,
                fecha_valuacion=date(2026, 10, 15),
                moneda="USD",
                valor_original=Decimal("1100.00"),
                equivalente_usd=Decimal("1100.00"),
                naturaleza_cotizacion="NO_APLICA",
                fuente_cotizacion=None,
                referencia="Corte",
            ),
        )
        self.resumen = SimpleNamespace(
            cantidad_flujos=1,
            cantidad_valuaciones=1,
            fecha_inicio=date(2026, 10, 1),
            fecha_valuacion=date(2026, 10, 15),
            aportes_inversion_usd_ref=Decimal("1000.00"),
            cobros_y_rescates_usd_ref=Decimal("0.00"),
            costos_externos_usd_ref=Decimal("0.00"),
            valor_mercado_final_usd_ref=Decimal("1100.00"),
            resultado_total_usd_ref=Decimal("100.00"),
            xirr_anual=Decimal("0.10"),
            mensaje_xirr="XIRR de prueba",
        )

    def listar_flujos_inversion(self, plan_id, limite=100):
        self.llamadas.append(("flujos", plan_id, limite))
        return self.flujos

    def listar_valuaciones_inversion(self, plan_id, limite=100):
        self.llamadas.append(("valuaciones", plan_id, limite))
        return self.valuaciones

    def resumen_rendimiento_inversion(self, plan_id):
        self.llamadas.append(("resumen", plan_id))
        return self.resumen


def test_consulta_entrega_dtos_y_preserva_el_resumen_de_la_fuente():
    fuente = _FuenteHistorialFalsa()

    historial = ConsultaHistorialInversionReposicion(fuente).obtener(12, limite=50)

    assert historial.flujos[0].id == 7
    assert historial.flujos[0].equivalente_usd == Decimal("1000.00")
    assert historial.valuaciones[0].id == 9
    assert historial.valuaciones[0].valor_original == Decimal("1100.00")
    assert historial.resumen.resultado_total_usd_ref == Decimal("100.00")
    assert historial.resumen.xirr_anual == Decimal("0.10")
    assert fuente.llamadas == [
        ("flujos", 12, 50),
        ("valuaciones", 12, 50),
        ("resumen", 12),
    ]


@pytest.mark.parametrize(
    "plan_id,limite",
    [
        (0, 100),
        (True, 100),
        (12, 0),
        (12, 101),
        (12, True),
    ],
)
def test_consulta_rechaza_identificadores_o_limites_invalidos(plan_id, limite):
    consulta = ConsultaHistorialInversionReposicion(_FuenteHistorialFalsa())

    with pytest.raises(ErrorValidacion):
        consulta.obtener(plan_id, limite=limite)


def test_fabrica_sqlite_conserva_historial_integridad_y_xirr(tmp_path):
    with BaseDatos(tmp_path / "historial_inversion.db") as db:
        aplicar_migraciones(db)
        repo = PlanesReposicionRepo(db)
        plan_id = repo.guardar_snapshot(
            nombre="Cartera familiar",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date.today() - timedelta(days=400),
            capital_original_ars=Decimal("12000000.00"),
            datos={
                "esquema_snapshot": 1,
                "supuestos": {"benchmark": "Cartera alternativa"},
                "resultado": {"capital_inicial_usd": Decimal("1000.00")},
            },
            creado_por="operador",
        )
        fecha_aporte = date.today() - timedelta(days=365)
        repo.registrar_flujo_inversion(
            plan_id,
            fecha_flujo=fecha_aporte,
            tipo_flujo="APORTE_INVERSION",
            moneda="USD",
            monto_original=Decimal("1000.00"),
            naturaleza_cotizacion="NO_APLICA",
            referencia="Aporte real",
            creado_por="operador",
        )
        repo.registrar_valoracion_inversion(
            plan_id,
            fecha_valuacion=date.today(),
            moneda="USD",
            valor_original=Decimal("1100.00"),
            naturaleza_cotizacion="NO_APLICA",
            referencia="Cierre declarado",
            creado_por="operador",
        )

        historial = crear_consulta_historial_inversion_reposicion(db).obtener(
            plan_id
        )

        assert len(historial.flujos) == 1
        assert historial.flujos[0].fecha_flujo == fecha_aporte
        assert historial.flujos[0].equivalente_usd == Decimal("1000.00")
        assert len(historial.valuaciones) == 1
        assert historial.valuaciones[0].fecha_valuacion == date.today()
        assert historial.valuaciones[0].equivalente_usd == Decimal("1100.00")
        assert historial.resumen.cantidad_flujos == 1
        assert historial.resumen.cantidad_valuaciones == 1
        assert historial.resumen.aportes_inversion_usd_ref == Decimal("1000.00")
        assert historial.resumen.valor_mercado_final_usd_ref == Decimal("1100.00")
        assert historial.resumen.resultado_total_usd_ref == Decimal("100.00")
        assert historial.resumen.xirr_anual == pytest.approx(
            Decimal("0.10"), abs=Decimal("0.005")
        )
