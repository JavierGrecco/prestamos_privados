"""Pruebas para snapshots persistentes del análisis de reposición."""
from datetime import date
from decimal import Decimal
import json

import pytest

from dominio.excepciones import ErrorValidacion
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PlanesReposicionRepo


@pytest.fixture
def repo(tmp_path):
    with BaseDatos(tmp_path / "reposicion.db") as db:
        aplicar_migraciones(db)
        yield db, PlanesReposicionRepo(db)


def _datos():
    return {
        "esquema_snapshot": 1,
        "supuestos": {
            "capital_ars": Decimal("12000000.00"),
            "fecha": date(2026, 10, 10),
            "tasa_benchmark": Decimal("0.0425"),
        },
        "resultado": {
            "capital_inicial_usd": Decimal("12000.00"),
            "brecha_final_usd": Decimal("-315.27"),
        },
    }


def test_guarda_y_recupera_snapshot_con_hash_verificable(repo):
    db, planes = repo
    snapshot_id = planes.guardar_snapshot(
        nombre="Auto familiar",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date(2026, 10, 10),
        capital_original_ars=Decimal("12000000.00"),
        datos=_datos(),
        creado_por="admin",
    )
    snapshot = planes.obtener_snapshot(snapshot_id)

    assert snapshot is not None
    assert snapshot.nombre == "Auto familiar"
    assert snapshot.tipo_plan == "REPOSICION_INTERNA"
    assert snapshot.capital_original_ars == Decimal("12000000.00")
    assert planes.verificar_snapshot(snapshot)
    payload = json.loads(snapshot.snapshot_json)
    assert payload["supuestos"]["capital_ars"] == "12000000.00"
    assert payload["supuestos"]["fecha"] == "2026-10-10"
    assert payload["resultado"]["brecha_final_usd"] == "-315.27"


def test_lista_resumenes_sin_cargar_json_completo(repo):
    _, planes = repo
    planes.guardar_snapshot(
        nombre="Plan 1",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date(2026, 10, 10),
        capital_original_ars=Decimal("1000"),
        datos=_datos(),
        creado_por="admin",
    )
    resumen = planes.listar_resumenes()[0]
    assert resumen.snapshot_json is None
    assert resumen.nombre == "Plan 1"


def test_version_de_plan_es_inmutable(repo):
    db, planes = repo
    snapshot_id = planes.guardar_snapshot(
        nombre="Plan inmutable",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date(2026, 10, 10),
        capital_original_ars=Decimal("1000"),
        datos=_datos(),
        creado_por="admin",
    )
    with pytest.raises(Exception, match="inmutable"):
        db.ejecutar(
            "UPDATE planes_reposicion_versiones SET snapshot_json = '{}' WHERE plan_id = ?",
            (snapshot_id,),
        )
    with pytest.raises(Exception, match="inmutable"):
        db.ejecutar(
            "DELETE FROM planes_reposicion_versiones WHERE plan_id = ?",
            (snapshot_id,),
        )


def test_rechaza_float_y_datos_invalidos(repo):
    _, planes = repo
    with pytest.raises(ErrorValidacion, match="no admite float"):
        planes.guardar_snapshot(
            nombre="Plan",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date(2026, 10, 10),
            capital_original_ars=Decimal("1000"),
            datos={"resultado": {"capital": 1.25}},
            creado_por="admin",
        )
    with pytest.raises(ErrorValidacion, match="tipo de plan"):
        planes.guardar_snapshot(
            nombre="Plan",
            tipo_plan="DESCONOCIDO",
            fecha_desembolso=date(2026, 10, 10),
            capital_original_ars=Decimal("1000"),
            datos=_datos(),
            creado_por="admin",
        )
    with pytest.raises(ErrorValidacion, match="capital original"):
        planes.guardar_snapshot(
            nombre="Plan",
            tipo_plan="REPOSICION_INTERNA",
            fecha_desembolso=date(2026, 10, 10),
            capital_original_ars=Decimal("0"),
            datos=_datos(),
            creado_por="admin",
        )


def test_rechaza_snapshot_tamperado(repo):
    _, planes = repo
    snapshot_id = planes.guardar_snapshot(
        nombre="Plan",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date(2026, 10, 10),
        capital_original_ars=Decimal("1000"),
        datos=_datos(),
        creado_por="admin",
    )
    snapshot = planes.obtener_snapshot(snapshot_id)
    tamperado = type(snapshot)(
        id=snapshot.id,
        nombre=snapshot.nombre,
        tipo_plan=snapshot.tipo_plan,
        fecha_desembolso=snapshot.fecha_desembolso,
        capital_original_ars=snapshot.capital_original_ars,
        snapshot_sha256=snapshot.snapshot_sha256,
        creado_por=snapshot.creado_por,
        creado_en=snapshot.creado_en,
        snapshot_json=snapshot.snapshot_json + " ",
    )
    assert not planes.verificar_snapshot(tamperado)



def test_guarda_versiones_consecutivas_sin_sobrescribir_historial(repo):
    _, planes = repo
    plan_id = planes.guardar_snapshot(
        nombre="Auto familiar",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date(2026, 10, 10),
        capital_original_ars=Decimal("12000000"),
        datos=_datos(),
        creado_por="admin",
    )
    datos_actualizados = _datos()
    datos_actualizados["resultado"]["brecha_final_usd"] = Decimal("125.00")
    version_dos = planes.guardar_nueva_version(
        plan_id, datos=datos_actualizados, creado_por="admin"
    )
    assert version_dos == 2
    plan = planes.obtener_plan(plan_id)
    assert plan is not None and plan.ultima_version == 2
    anterior = planes.obtener_version(plan_id, 1)
    actual = planes.obtener_version(plan_id, 2)
    assert anterior is not None and actual is not None
    assert planes.verificar_version(anterior)
    assert planes.verificar_version(actual)
    assert json.loads(anterior.snapshot_json)["resultado"]["brecha_final_usd"] == "-315.27"
    assert json.loads(actual.snapshot_json)["resultado"]["brecha_final_usd"] == "125.00"


def test_cerrar_plan_conserva_historial_y_bloquea_nuevas_versiones(repo):
    db, planes = repo
    plan_id = planes.guardar_snapshot(
        nombre="Plan cerrado",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date(2026, 10, 10),
        capital_original_ars=Decimal("1000"),
        datos=_datos(),
        creado_por="admin",
    )
    planes.cerrar_plan(plan_id, cerrado_por="admin")
    plan = planes.obtener_plan(plan_id)
    assert plan is not None and plan.estado == "CERRADO"
    assert plan.cerrado_por == "admin"
    assert len(planes.listar_versiones(plan_id)) == 1
    with pytest.raises(ErrorValidacion, match="cerrado"):
        planes.guardar_nueva_version(plan_id, datos=_datos(), creado_por="admin")
    with pytest.raises(Exception, match="inmutables"):
        db.ejecutar(
            "UPDATE planes_reposicion SET nombre = 'otro' WHERE id = ?",
            (plan_id,),
        )
