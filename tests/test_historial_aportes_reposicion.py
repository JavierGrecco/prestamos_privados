"""Pruebas de la consulta del historial de aportes de reposición."""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from aplicacion.consultas.historial_aportes_reposicion import (
    ConsultaHistorialAportesReposicion,
)
from infraestructura import BaseDatos
from infraestructura.composicion.historial_aportes_reposicion import (
    crear_consulta_historial_aportes_reposicion,
)
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PlanesReposicionRepo


class _FuenteAportesFalsa:
    def __init__(self):
        self.llamadas = []
        self.aportes = (
            SimpleNamespace(
                id=2,
                fecha_aporte=date(2026, 10, 15),
                monto_ars=Decimal("800000.00"),
                cotizacion_ars_por_usd=Decimal("1600.000000"),
                equivalente_usd=Decimal("500.00"),
                naturaleza_cotizacion="SUPUESTO",
                fuente_cotizacion=None,
                referencia="Aporte más reciente",
            ),
            SimpleNamespace(
                id=1,
                fecha_aporte=date(2026, 10, 14),
                monto_ars=Decimal("1500000.00"),
                cotizacion_ars_por_usd=Decimal("1500.000000"),
                equivalente_usd=Decimal("1000.00"),
                naturaleza_cotizacion="OBSERVADA",
                fuente_cotizacion="Fuente identificada",
                referencia="Aporte anterior",
            ),
        )

    def listar_aportes(self, plan_id, limite=200):
        self.llamadas.append((plan_id, limite))
        return self.aportes


def test_consulta_devuelve_dtos_en_el_orden_de_la_fuente():
    fuente = _FuenteAportesFalsa()

    aportes = ConsultaHistorialAportesReposicion(fuente).listar(25)

    assert [aporte.id for aporte in aportes] == [2, 1]
    assert [aporte.equivalente_usd for aporte in aportes] == [
        Decimal("500.00"),
        Decimal("1000.00"),
    ]
    assert aportes[0].cotizacion_ars_por_usd == Decimal("1600.000000")
    assert aportes[1].fuente_cotizacion == "Fuente identificada"
    assert fuente.llamadas == [(25, 200)]


def test_fabrica_sqlite_conserva_orden_y_equivalencias_historicas(tmp_path):
    with BaseDatos(tmp_path / "historial_aportes.db") as db:
        aplicar_migraciones(db)
        repo = PlanesReposicionRepo(db)
        plan_id = repo.guardar_snapshot(
            nombre="Reposición auto familiar",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date.today() - timedelta(days=30),
            capital_original_ars=Decimal("12000000.00"),
            datos={
                "esquema_snapshot": 1,
                "supuestos": {"benchmark": "Cartera declarada"},
                "resultado": {"capital_inicial_usd": Decimal("12000.00")},
            },
            creado_por="operador",
        )
        fecha_antigua = date.today() - timedelta(days=2)
        fecha_reciente = date.today() - timedelta(days=1)

        repo.registrar_aporte(
            plan_id,
            fecha_aporte=fecha_antigua,
            monto_ars=Decimal("1500000.00"),
            cotizacion_ars_por_usd=Decimal("1500.000000"),
            naturaleza_cotizacion="OBSERVADA",
            fuente_cotizacion="Cotización usada en el primer aporte",
            referencia="Aporte anterior",
            nota="Ahorro inicial",
            creado_por="operador",
        )
        repo.registrar_aporte(
            plan_id,
            fecha_aporte=fecha_reciente,
            monto_ars=Decimal("800000.00"),
            cotizacion_ars_por_usd=Decimal("1600.000000"),
            naturaleza_cotizacion="SUPUESTO",
            fuente_cotizacion="",
            referencia="Aporte más reciente",
            nota="Ahorro adicional",
            creado_por="operador",
        )

        auditoria_antes = db.consultar_uno(
            "SELECT COUNT(*) AS cantidad FROM auditoria"
        )["cantidad"]
        aportes = crear_consulta_historial_aportes_reposicion(db).listar(plan_id)
        auditoria_despues = db.consultar_uno(
            "SELECT COUNT(*) AS cantidad FROM auditoria"
        )["cantidad"]

        assert [aporte.fecha_aporte for aporte in aportes] == [
            fecha_reciente, fecha_antigua
        ]
        assert [aporte.referencia for aporte in aportes] == [
            "Aporte más reciente", "Aporte anterior"
        ]
        assert sum((aporte.monto_ars for aporte in aportes), Decimal("0")) == Decimal(
            "2300000.00"
        )
        assert sum(
            (aporte.equivalente_usd for aporte in aportes), Decimal("0")
        ) == Decimal("1500.00")
        assert aportes[0].cotizacion_ars_por_usd == Decimal("1600.000000")
        assert aportes[1].cotizacion_ars_por_usd == Decimal("1500.000000")
        assert auditoria_despues == auditoria_antes
