"""Pruebas del caso de uso para guardar análisis y nuevas versiones."""

from datetime import date
from decimal import Decimal

import pytest

from aplicacion.servicios.guardar_analisis_reposicion import (
    ServicioGuardarAnalisisReposicion,
)
from dominio.excepciones import ErrorValidacion
from infraestructura import BaseDatos
from infraestructura.composicion.guardar_analisis_reposicion import (
    crear_servicio_guardado_analisis_reposicion,
)
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PlanesReposicionRepo


class _RepositorioFalso:
    def __init__(self):
        self.creaciones = []
        self.versiones = []

    def crear_plan_con_snapshot(self, **kwargs):
        self.creaciones.append(kwargs)
        return 27, 1

    def guardar_nueva_version(self, plan_id, **kwargs):
        self.versiones.append((plan_id, kwargs))
        return 3


def _argumentos(**cambios):
    valores = {
        "plan_id_destino": None,
        "crear_nuevo": True,
        "nombre": "Auto familiar",
        "tipo_plan": "REPOSICION_INTERNA",
        "fecha_desembolso": date(2026, 10, 1),
        "capital_original_ars": Decimal("12000000.00"),
        "datos": {
            "supuestos": {"benchmark": "Prueba"},
            "resultado": {"capital_inicial_usd": Decimal("12000.00")},
        },
        "creado_por": "operador",
    }
    valores.update(cambios)
    return valores


def test_crea_plan_y_primera_version_a_traves_del_puerto():
    repositorio = _RepositorioFalso()

    resultado = ServicioGuardarAnalisisReposicion(repositorio).guardar(
        **_argumentos()
    )

    assert resultado.plan_id == 27
    assert resultado.numero_version == 1
    assert resultado.creado_nuevo
    assert len(repositorio.creaciones) == 1
    assert repositorio.creaciones[0]["nombre"] == "Auto familiar"
    assert repositorio.creaciones[0]["creado_por"] == "operador"
    assert repositorio.versiones == []


def test_guarda_version_en_el_plan_elegido_sin_crear_otro():
    repositorio = _RepositorioFalso()

    resultado = ServicioGuardarAnalisisReposicion(repositorio).guardar(
        **_argumentos(crear_nuevo=False, plan_id_destino=27)
    )

    assert resultado.plan_id == 27
    assert resultado.numero_version == 3
    assert not resultado.creado_nuevo
    assert repositorio.creaciones == []
    assert repositorio.versiones[0][0] == 27
    assert repositorio.versiones[0][1]["creado_por"] == "operador"


@pytest.mark.parametrize(
    "cambios, mensaje",
    [
        ({"creado_por": "  "}, "No se identificó la cuenta"),
        (
            {"crear_nuevo": False, "plan_id_destino": None},
            "Seleccioná un plan activo",
        ),
        (
            {"crear_nuevo": False, "plan_id_destino": 0},
            "Seleccioná un plan activo",
        ),
        ({"crear_nuevo": "sí"}, "opción para guardar"),
    ],
)
def test_rechaza_entradas_invalidas_sin_escribir(cambios, mensaje):
    repositorio = _RepositorioFalso()

    with pytest.raises(ErrorValidacion, match=mensaje):
        ServicioGuardarAnalisisReposicion(repositorio).guardar(
            **_argumentos(**cambios)
        )

    assert repositorio.creaciones == []
    assert repositorio.versiones == []


def test_fabrica_guarda_plan_y_versiones_sin_sobrescribir_historial(tmp_path):
    with BaseDatos(tmp_path / "guardado_analisis.db") as db:
        aplicar_migraciones(db)
        repo = PlanesReposicionRepo(db)
        servicio = crear_servicio_guardado_analisis_reposicion(db)
        datos_iniciales = {
            "esquema_snapshot": 1,
            "supuestos": {"benchmark": "Cartera inicial"},
            "resultado": {"brecha_final_usd": Decimal("-315.27")},
        }

        inicial = servicio.guardar(
            crear_nuevo=True,
            plan_id_destino=None,
            nombre="Auto familiar",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date(2026, 10, 1),
            capital_original_ars=Decimal("12000000.00"),
            datos=datos_iniciales,
            creado_por="test",
        )
        assert inicial.creado_nuevo
        assert inicial.numero_version == 1

        datos_nuevos = {
            "esquema_snapshot": 1,
            "supuestos": {"benchmark": "Cartera revisada"},
            "resultado": {"brecha_final_usd": Decimal("125.00")},
        }
        siguiente = servicio.guardar(
            crear_nuevo=False,
            plan_id_destino=inicial.plan_id,
            nombre="No se usa al versionar",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date(2026, 10, 1),
            capital_original_ars=Decimal("12000000.00"),
            datos=datos_nuevos,
            creado_por="test",
        )

        assert not siguiente.creado_nuevo
        assert siguiente.plan_id == inicial.plan_id
        assert siguiente.numero_version == 2
        plan = repo.obtener_plan(inicial.plan_id)
        anterior = repo.obtener_version(inicial.plan_id, 1)
        actual = repo.obtener_version(inicial.plan_id, 2)
        assert plan is not None and plan.ultima_version == 2
        assert anterior is not None and repo.verificar_version(anterior)
        assert actual is not None and repo.verificar_version(actual)
        assert repo.listar_versiones(inicial.plan_id)[0].numero_version == 1
        assert repo.listar_versiones(inicial.plan_id)[1].numero_version == 2
