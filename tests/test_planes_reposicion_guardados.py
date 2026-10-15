"""Pruebas de lectura y verificación de planes de reposición guardados."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from aplicacion.consultas.planes_reposicion_guardados import (
    ConsultaPlanesReposicionGuardados,
)
from dominio.excepciones import ErrorValidacion
from infraestructura import BaseDatos
from infraestructura.composicion.planes_reposicion_guardados import (
    crear_consulta_planes_reposicion_guardados,
)
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PlanesReposicionRepo


class _FuentePlanesFalsa:
    def __init__(self):
        self.planes = [
            SimpleNamespace(
                id=1,
                nombre="Auto familiar",
                tipo_plan="REPOSICION_INTERNA",
                capital_original_ars=Decimal("12000000.00"),
                estado="ACTIVO",
                ultima_version=2,
            ),
            SimpleNamespace(
                id=2,
                nombre="Préstamo entre personas",
                tipo_plan="PRESTAMO_ENTRE_PERSONAS",
                capital_original_ars=Decimal("4500000.00"),
                estado="CERRADO",
                ultima_version=1,
            ),
        ]
        self.versiones = {
            (1, 2): SimpleNamespace(
                id=22,
                plan_id=1,
                numero_version=2,
                snapshot_sha256="sha256-validado",
                creado_por="operador",
                creado_en="2026-10-15T10:00:00",
                snapshot_json='{"resultado":{"total_programado_usd":"9000.00"}}',
                integra=True,
            ),
            (1, 1): SimpleNamespace(
                id=21,
                plan_id=1,
                numero_version=1,
                snapshot_sha256="sha256-alterado",
                creado_por="operador",
                creado_en="2026-10-14T10:00:00",
                snapshot_json='{"resultado":{}}',
                integra=False,
            ),
            (2, 1): SimpleNamespace(
                id=31,
                plan_id=2,
                numero_version=1,
                snapshot_sha256="sha256-invalido-json",
                creado_por="operador",
                creado_en="2026-10-13T10:00:00",
                snapshot_json="{no es json",
                integra=True,
            ),
        }
        self.listar_args = []

    def listar_planes(self, limite=30, *, solo_activos=False):
        self.listar_args.append((limite, solo_activos))
        planes = self.planes
        if solo_activos:
            planes = [plan for plan in planes if plan.estado == "ACTIVO"]
        return planes[:limite]

    def obtener_plan(self, plan_id):
        return next((plan for plan in self.planes if plan.id == plan_id), None)

    def listar_versiones(self, plan_id):
        return [
            version
            for (id_plan, _), version in sorted(self.versiones.items())
            if id_plan == plan_id
        ]

    def obtener_version(self, plan_id, numero_version):
        return self.versiones.get((plan_id, numero_version))

    def verificar_version(self, version):
        return version.integra


def test_lista_planes_como_datos_tipados_y_respeta_filtro_de_activos():
    fuente = _FuentePlanesFalsa()
    consulta = ConsultaPlanesReposicionGuardados(fuente)

    todos = consulta.listar_planes(limite=30)
    activos = consulta.listar_planes(limite=5, solo_activos=True)

    assert [plan.nombre for plan in todos] == [
        "Auto familiar",
        "Préstamo entre personas",
    ]
    assert todos[0].capital_original_ars == Decimal("12000000.00")
    assert [plan.id for plan in activos] == [1]
    assert fuente.listar_args == [(30, False), (5, True)]


def test_version_valida_devuelve_el_snapshot_decodificado():
    consulta = ConsultaPlanesReposicionGuardados(_FuentePlanesFalsa())

    version = consulta.obtener_version(1, 2)

    assert version is not None
    assert version.integridad_valida
    assert version.contenido_valido
    assert version.contenido == {
        "resultado": {"total_programado_usd": "9000.00"}
    }
    assert version.snapshot_sha256 == "sha256-validado"


def test_version_con_huella_invalida_no_expone_el_snapshot():
    consulta = ConsultaPlanesReposicionGuardados(_FuentePlanesFalsa())

    version = consulta.obtener_version(1, 1)

    assert version is not None
    assert not version.integridad_valida
    assert not version.contenido_valido
    assert version.contenido is None


def test_version_con_json_invalido_se_devuelve_como_contenido_no_valido():
    consulta = ConsultaPlanesReposicionGuardados(_FuentePlanesFalsa())

    version = consulta.obtener_version(2, 1)

    assert version is not None
    assert version.integridad_valida
    assert not version.contenido_valido
    assert version.contenido is None


def test_consulta_rechaza_identificadores_y_limites_invalidos():
    consulta = ConsultaPlanesReposicionGuardados(_FuentePlanesFalsa())

    with pytest.raises(ErrorValidacion, match="entero positivo"):
        consulta.listar_planes(limite=0)
    with pytest.raises(ErrorValidacion, match="identificador de plan"):
        consulta.obtener_plan(0)
    with pytest.raises(ErrorValidacion, match="identificador de versión"):
        consulta.obtener_version(1, -1)


def test_fabrica_sqlite_lee_plan_y_verifica_version_guardada(tmp_path):
    with BaseDatos(tmp_path / "planes_guardados.db") as db:
        aplicar_migraciones(db)
        repo = PlanesReposicionRepo(db)
        plan_id, version_nro = repo.crear_plan_con_snapshot(
            nombre="Auto familiar",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date(2026, 10, 1),
            capital_original_ars=Decimal("12000000.00"),
            datos={
                "esquema_snapshot": 1,
                "supuestos": {"benchmark": "Cartera de referencia"},
                "resultado": {
                    "capital_inicial_usd": Decimal("12000.00"),
                    "cuotas": [],
                },
            },
            creado_por="test",
        )

        consulta = crear_consulta_planes_reposicion_guardados(db)
        planes = consulta.listar_planes()
        plan = consulta.obtener_plan(plan_id)
        numeros = consulta.listar_versiones(plan_id)
        version = consulta.obtener_version(plan_id, version_nro)

        assert [item.id for item in planes] == [plan_id]
        assert plan is not None
        assert plan.nombre == "Auto familiar"
        assert plan.ultima_version == 1
        assert numeros == (1,)
        assert version is not None
        assert version.integridad_valida
        assert version.contenido_valido
        assert version.contenido["resultado"]["capital_inicial_usd"] == "12000.00"
