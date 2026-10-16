"""Pruebas del caso de uso para cerrar planes de reposición."""

from datetime import date
from decimal import Decimal

import pytest

from aplicacion.servicios.cerrar_plan_reposicion import ServicioCerrarPlanReposicion
from dominio.excepciones import ErrorValidacion
from infraestructura import BaseDatos
from infraestructura.composicion.cerrar_plan_reposicion import (
    crear_servicio_cerrar_plan_reposicion,
)
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PlanesReposicionRepo


class _RepositorioCierreFalso:
    def __init__(self):
        self.llamadas = []

    def cerrar_plan(self, plan_id, *, cerrado_por):
        self.llamadas.append((plan_id, cerrado_por))


def test_servicio_delega_plan_y_operador_sin_modificar_datos():
    repositorio = _RepositorioCierreFalso()

    ServicioCerrarPlanReposicion(repositorio).cerrar(12, cerrado_por="operador")

    assert repositorio.llamadas == [(12, "operador")]


def test_cierre_sqlite_conserva_snapshot_y_bloquea_nuevas_operaciones(tmp_path):
    with BaseDatos(tmp_path / "cierre_plan_use_case.db") as db:
        aplicar_migraciones(db)
        repo = PlanesReposicionRepo(db)
        plan_id, version_numero = repo.crear_plan_con_snapshot(
            nombre="Plan de reposición",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date.today(),
            capital_original_ars=Decimal("12000000.00"),
            datos={
                "esquema_snapshot": 1,
                "supuestos": {"benchmark": "Cartera de referencia"},
                "resultado": {"brecha_final_usd": Decimal("-315.27")},
            },
            creado_por="operador",
        )
        assert version_numero == 1

        crear_servicio_cerrar_plan_reposicion(db).cerrar(
            plan_id, cerrado_por="operador"
        )

        plan = repo.obtener_plan(plan_id)
        version = repo.obtener_version(plan_id, 1)
        assert plan is not None
        assert plan.estado == "CERRADO"
        assert plan.cerrado_por == "operador"
        assert plan.ultima_version == 1
        assert version is not None
        assert repo.verificar_version(version)
        assert len(repo.listar_versiones(plan_id)) == 1

        with pytest.raises(ErrorValidacion, match="cerrado"):
            repo.guardar_nueva_version(
                plan_id,
                datos={
                    "esquema_snapshot": 1,
                    "supuestos": {"benchmark": "Cambio"},
                    "resultado": {"brecha_final_usd": Decimal("0.00")},
                },
                creado_por="operador",
            )

        # El cierre también debe impedir nuevas operaciones financieras,
        # pero mantener accesible el historial que ya fue guardado.
        with pytest.raises(ErrorValidacion):
            repo.registrar_aporte(
                plan_id,
                fecha_aporte=date.today(),
                monto_ars=Decimal("1500000.00"),
                cotizacion_ars_por_usd=Decimal("1500.000000"),
                naturaleza_cotizacion="SUPUESTO",
                fuente_cotizacion="",
                referencia="Aporte posterior al cierre",
                nota="No debe guardarse",
                creado_por="operador",
            )

        with pytest.raises(ErrorValidacion):
            repo.registrar_flujo_inversion(
                plan_id,
                fecha_flujo=date.today(),
                tipo_flujo="APORTE_INVERSION",
                moneda="USD",
                monto_original=Decimal("100.00"),
                naturaleza_cotizacion="NO_APLICA",
                creado_por="operador",
            )

        with pytest.raises(ErrorValidacion):
            repo.registrar_valoracion_inversion(
                plan_id,
                fecha_valuacion=date.today(),
                moneda="USD",
                valor_original=Decimal("100.00"),
                naturaleza_cotizacion="NO_APLICA",
                creado_por="operador",
            )

        # Ninguna operación rechazada sobrescribe ni agrega una versión.
        version_despues = repo.obtener_version(plan_id, 1)
        assert version_despues is not None
        assert repo.verificar_version(version_despues)
        assert len(repo.listar_versiones(plan_id)) == 1
