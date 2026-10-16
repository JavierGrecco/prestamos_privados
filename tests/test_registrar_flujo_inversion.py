"""Pruebas para el caso de uso de registro de flujos de inversión."""

from datetime import date
from decimal import Decimal

from aplicacion.servicios.registrar_flujo_inversion import (
    ServicioRegistrarFlujoInversion,
)
from infraestructura import BaseDatos
from infraestructura.composicion.registrar_flujo_inversion import (
    crear_servicio_registrar_flujo_inversion,
)
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PlanesReposicionRepo


class _RepositorioFlujosFalso:
    def __init__(self):
        self.llamadas = []

    def registrar_flujo_inversion(self, plan_id, **kwargs):
        self.llamadas.append((plan_id, kwargs))
        return 41


def test_servicio_delega_los_datos_del_flujo_sin_recalcular():
    repositorio = _RepositorioFlujosFalso()
    servicio = ServicioRegistrarFlujoInversion(repositorio)

    flujo_id = servicio.registrar(
        8,
        fecha_flujo=date(2026, 10, 15),
        tipo_flujo="APORTE_INVERSION",
        moneda="ARS",
        monto_original=Decimal("1500000.00"),
        cotizacion_ars_por_usd=Decimal("1500.000000"),
        naturaleza_cotizacion="OBSERVADA",
        fuente_cotizacion="Fuente identificada",
        referencia="Compra para cartera",
        nota="Movimiento declarado",
        creado_por="operador",
    )

    assert flujo_id == 41
    assert repositorio.llamadas == [
        (
            8,
            {
                "fecha_flujo": date(2026, 10, 15),
                "tipo_flujo": "APORTE_INVERSION",
                "moneda": "ARS",
                "monto_original": Decimal("1500000.00"),
                "cotizacion_ars_por_usd": Decimal("1500.000000"),
                "naturaleza_cotizacion": "OBSERVADA",
                "fuente_cotizacion": "Fuente identificada",
                "referencia": "Compra para cartera",
                "nota": "Movimiento declarado",
                "creado_por": "operador",
            },
        )
    ]


def test_fabrica_registra_flujo_ars_con_equivalencia_y_hash(tmp_path):
    with BaseDatos(tmp_path / "registro_flujo_use_case.db") as db:
        aplicar_migraciones(db)
        repo = PlanesReposicionRepo(db)
        plan_id, version = repo.crear_plan_con_snapshot(
            nombre="Cartera familiar",
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

        flujo_id = crear_servicio_registrar_flujo_inversion(db).registrar(
            plan_id,
            fecha_flujo=date.today(),
            tipo_flujo="APORTE_INVERSION",
            moneda="ARS",
            monto_original=Decimal("1500000.00"),
            cotizacion_ars_por_usd=Decimal("1500.000000"),
            naturaleza_cotizacion="OBSERVADA",
            fuente_cotizacion="Cotización comprobada en la prueba",
            referencia="Compra declarada",
            nota="Movimiento separado de reposición",
            creado_por="operador",
        )

        flujo = repo.obtener_flujo_inversion(flujo_id)
        assert flujo is not None
        assert flujo.plan_id == plan_id
        assert flujo.tipo_flujo == "APORTE_INVERSION"
        assert flujo.moneda == "ARS"
        assert flujo.monto_original == Decimal("1500000.00")
        assert flujo.cotizacion_ars_por_usd == Decimal("1500.000000")
        assert flujo.equivalente_usd == Decimal("1000.00")
        assert flujo.naturaleza_cotizacion == "OBSERVADA"
        assert flujo.creado_por == "operador"
        assert repo.verificar_flujo_inversion(flujo)
