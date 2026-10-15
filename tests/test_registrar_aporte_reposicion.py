"""Pruebas para el caso de uso de registro de aportes de reposición."""

from datetime import date
from decimal import Decimal

from aplicacion.servicios.registrar_aporte_reposicion import (
    ServicioRegistrarAporteReposicion,
)
from infraestructura import BaseDatos
from infraestructura.composicion.registrar_aporte_reposicion import (
    crear_servicio_registrar_aporte_reposicion,
)
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PlanesReposicionRepo


class _RepositorioAportesFalso:
    def __init__(self):
        self.llamadas = []

    def registrar_aporte(self, plan_id, **kwargs):
        self.llamadas.append((plan_id, kwargs))
        return 19


def test_servicio_delega_los_datos_sin_recalcular_importes():
    repositorio = _RepositorioAportesFalso()
    servicio = ServicioRegistrarAporteReposicion(repositorio)
    argumentos = {
        "plan_id": 7,
        "fecha_aporte": date(2026, 10, 15),
        "monto_ars": Decimal("1500000.00"),
        "cotizacion_ars_por_usd": Decimal("1500.000000"),
        "naturaleza_cotizacion": "OBSERVADA",
        "fuente_cotizacion": "Fuente identificada",
        "referencia": "Aporte de prueba",
        "nota": "Reservado para reponer capital",
        "creado_por": "operador",
    }

    aporte_id = servicio.registrar(**argumentos)

    assert aporte_id == 19
    assert repositorio.llamadas == [
        (
            7,
            {
                "fecha_aporte": date(2026, 10, 15),
                "monto_ars": Decimal("1500000.00"),
                "cotizacion_ars_por_usd": Decimal("1500.000000"),
                "naturaleza_cotizacion": "OBSERVADA",
                "fuente_cotizacion": "Fuente identificada",
                "referencia": "Aporte de prueba",
                "nota": "Reservado para reponer capital",
                "creado_por": "operador",
            },
        )
    ]


def test_fabrica_registra_aporte_con_equivalencia_y_hash_verificable(tmp_path):
    with BaseDatos(tmp_path / "aporte_reposicion_use_case.db") as db:
        aplicar_migraciones(db)
        repo = PlanesReposicionRepo(db)
        plan_id, version = repo.crear_plan_con_snapshot(
            nombre="Auto familiar",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date.today(),
            capital_original_ars=Decimal("12000000.00"),
            datos={
                "esquema_snapshot": 1,
                "supuestos": {"benchmark": "Cartera de prueba"},
                "resultado": {"capital_inicial_usd": Decimal("12000.00")},
            },
            creado_por="operador",
        )
        assert version == 1

        aporte_id = crear_servicio_registrar_aporte_reposicion(db).registrar(
            plan_id,
            fecha_aporte=date.today(),
            monto_ars=Decimal("1500000.00"),
            cotizacion_ars_por_usd=Decimal("1500.000000"),
            naturaleza_cotizacion="OBSERVADA",
            fuente_cotizacion="Cotización registrada en la prueba",
            referencia="Aporte test",
            nota="Destinado a reposición",
            creado_por="operador",
        )

        aporte = repo.obtener_aporte(aporte_id)
        assert aporte is not None
        assert aporte.plan_id == plan_id
        assert aporte.monto_ars == Decimal("1500000.00")
        assert aporte.cotizacion_ars_por_usd == Decimal("1500.000000")
        assert aporte.equivalente_usd == Decimal("1000.00")
        assert aporte.naturaleza_cotizacion == "OBSERVADA"
        assert aporte.fuente_cotizacion == "Cotización registrada en la prueba"
        assert aporte.creado_por == "operador"
        assert repo.verificar_aporte(aporte)
