"""Pruebas del caso de uso para registrar valuaciones de inversión."""

from datetime import date
from decimal import Decimal

from aplicacion.servicios.registrar_valoracion_inversion import (
    ServicioRegistrarValoracionInversion,
)
from infraestructura import BaseDatos
from infraestructura.composicion.registrar_valoracion_inversion import (
    crear_servicio_registrar_valoracion_inversion,
)
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PlanesReposicionRepo


class _RepositorioValuacionesFalso:
    def __init__(self):
        self.llamadas = []

    def registrar_valoracion_inversion(self, plan_id, **kwargs):
        self.llamadas.append((plan_id, kwargs))
        return 52


def test_servicio_delega_datos_de_valuacion_sin_calcular_rendimiento():
    repositorio = _RepositorioValuacionesFalso()
    servicio = ServicioRegistrarValoracionInversion(repositorio)

    resultado = servicio.registrar(
        9,
        fecha_valuacion=date(2026, 10, 15),
        moneda="ARS",
        valor_original=Decimal("1650000.00"),
        cotizacion_ars_por_usd=Decimal("1500.000000"),
        naturaleza_cotizacion="OBSERVADA",
        fuente_cotizacion="Fuente identificada",
        referencia="Corte trimestral",
        nota="Saldo restante de inversión",
        creado_por="operador",
    )

    assert resultado == 52
    assert repositorio.llamadas == [
        (
            9,
            {
                "fecha_valuacion": date(2026, 10, 15),
                "moneda": "ARS",
                "valor_original": Decimal("1650000.00"),
                "cotizacion_ars_por_usd": Decimal("1500.000000"),
                "naturaleza_cotizacion": "OBSERVADA",
                "fuente_cotizacion": "Fuente identificada",
                "referencia": "Corte trimestral",
                "nota": "Saldo restante de inversión",
                "creado_por": "operador",
            },
        )
    ]


def test_fabrica_registra_valuacion_ars_con_equivalencia_y_hash(tmp_path):
    with BaseDatos(tmp_path / "registro_valoracion_use_case.db") as db:
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

        valoracion_id = crear_servicio_registrar_valoracion_inversion(db).registrar(
            plan_id,
            fecha_valuacion=date.today(),
            moneda="ARS",
            valor_original=Decimal("1650000.00"),
            cotizacion_ars_por_usd=Decimal("1500.000000"),
            naturaleza_cotizacion="OBSERVADA",
            fuente_cotizacion="Cotización comprobada en la prueba",
            referencia="Corte trimestral",
            nota="Saldo restante",
            creado_por="operador",
        )

        valoracion = repo.obtener_valoracion_inversion(valoracion_id)
        assert valoracion is not None
        assert valoracion.plan_id == plan_id
        assert valoracion.moneda == "ARS"
        assert valoracion.valor_original == Decimal("1650000.00")
        assert valoracion.cotizacion_ars_por_usd == Decimal("1500.000000")
        assert valoracion.equivalente_usd == Decimal("1100.00")
        assert valoracion.naturaleza_cotizacion == "OBSERVADA"
        assert valoracion.creado_por == "operador"
        assert repo.verificar_valoracion_inversion(valoracion)
