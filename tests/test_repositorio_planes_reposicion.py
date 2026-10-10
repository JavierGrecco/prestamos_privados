"""Pruebas para snapshots persistentes del análisis de reposición."""
from datetime import date, timedelta
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



def test_registra_aporte_de_reposicion_con_equivalencia_y_hash(repo):
    _, planes = repo
    plan_id = planes.guardar_snapshot(
        nombre="Reposición auto",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date(2026, 10, 1),
        capital_original_ars=Decimal("12000000"),
        datos=_datos(),
        creado_por="admin",
    )
    aporte_id = planes.registrar_aporte(
        plan_id,
        fecha_aporte=date(2026, 10, 9),
        monto_ars=Decimal("1500000.00"),
        cotizacion_ars_por_usd=Decimal("1500.000000"),
        naturaleza_cotizacion="OBSERVADA",
        fuente_cotizacion="Cotización registrada manualmente",
        referencia="Aporte de octubre",
        nota="Ahorro separado para reponer el capital",
        creado_por="admin",
    )
    aporte = planes.obtener_aporte(aporte_id)
    assert aporte is not None
    assert aporte.plan_id == plan_id
    assert aporte.monto_ars == Decimal("1500000.00")
    assert aporte.cotizacion_ars_por_usd == Decimal("1500.000000")
    assert aporte.equivalente_usd == Decimal("1000.00")
    assert aporte.naturaleza_cotizacion == "OBSERVADA"
    assert planes.verificar_aporte(aporte)
    resumen = planes.listar_aportes(plan_id)
    assert len(resumen) == 1
    assert resumen[0].snapshot_json is None


def test_aporte_solo_se_permite_en_plan_interno_activo(repo):
    _, planes = repo
    plan_externo = planes.guardar_snapshot(
        nombre="Préstamo entre personas",
        tipo_plan="PRESTAMO_ENTRE_PERSONAS",
        fecha_desembolso=date(2026, 10, 1),
        capital_original_ars=Decimal("1000"),
        datos=_datos(),
        creado_por="admin",
    )
    parametros = {
        "fecha_aporte": date(2026, 10, 9),
        "monto_ars": Decimal("100.00"),
        "cotizacion_ars_por_usd": Decimal("1000"),
        "naturaleza_cotizacion": "SUPUESTO",
        "fuente_cotizacion": "",
        "referencia": "",
        "nota": "",
        "creado_por": "admin",
    }
    with pytest.raises(ErrorValidacion, match="solo corresponden a un plan interno"):
        planes.registrar_aporte(plan_externo, **parametros)

    plan_interno = planes.guardar_snapshot(
        nombre="Plan interno cerrado",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date(2026, 10, 1),
        capital_original_ars=Decimal("1000"),
        datos=_datos(),
        creado_por="admin",
    )
    planes.cerrar_plan(plan_interno, cerrado_por="admin")
    with pytest.raises(ErrorValidacion, match="cerrado"):
        planes.registrar_aporte(plan_interno, **parametros)


def test_aporte_rechaza_montos_o_cotizaciones_invalidos(repo):
    _, planes = repo
    plan_id = planes.guardar_snapshot(
        nombre="Plan interno",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date(2026, 10, 1),
        capital_original_ars=Decimal("1000"),
        datos=_datos(),
        creado_por="admin",
    )
    kwargs = {
        "fecha_aporte": date(2026, 10, 9),
        "monto_ars": Decimal("100.001"),
        "cotizacion_ars_por_usd": Decimal("1000"),
        "naturaleza_cotizacion": "SUPUESTO",
        "fuente_cotizacion": "",
        "referencia": "",
        "nota": "",
        "creado_por": "admin",
    }
    with pytest.raises(ErrorValidacion, match="hasta 2 decimales"):
        planes.registrar_aporte(plan_id, **kwargs)
    kwargs["monto_ars"] = Decimal("100.00")
    kwargs["cotizacion_ars_por_usd"] = Decimal("0")
    with pytest.raises(ErrorValidacion, match="cotización"):
        planes.registrar_aporte(plan_id, **kwargs)


def test_aporte_es_inmutable(repo):
    db, planes = repo
    plan_id = planes.guardar_snapshot(
        nombre="Plan interno",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date(2026, 10, 1),
        capital_original_ars=Decimal("1000"),
        datos=_datos(),
        creado_por="admin",
    )
    aporte_id = planes.registrar_aporte(
        plan_id,
        fecha_aporte=date(2026, 10, 9),
        monto_ars=Decimal("100.00"),
        cotizacion_ars_por_usd=Decimal("1000"),
        naturaleza_cotizacion="SUPUESTO",
        fuente_cotizacion="",
        referencia="",
        nota="",
        creado_por="admin",
    )
    aporte = planes.obtener_aporte(aporte_id)
    assert aporte is not None and planes.verificar_aporte(aporte)
    with pytest.raises(Exception, match="inmutables"):
        db.ejecutar(
            "UPDATE aportes_reposicion SET monto_ars = '500' WHERE id = ?",
            (aporte_id,),
        )
    with pytest.raises(Exception, match="historial"):
        db.ejecutar("DELETE FROM aportes_reposicion WHERE id = ?", (aporte_id,))



def test_aporte_rechaza_fecha_futura_y_cotizacion_observada_sin_fuente(repo):
    _, planes = repo
    plan_id = planes.guardar_snapshot(
        nombre="Plan interno",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date(2026, 10, 1),
        capital_original_ars=Decimal("1000"),
        datos=_datos(),
        creado_por="admin",
    )
    datos = {
        "monto_ars": Decimal("100.00"),
        "cotizacion_ars_por_usd": Decimal("1000.00"),
        "naturaleza_cotizacion": "OBSERVADA",
        "fuente_cotizacion": "",
        "referencia": "",
        "nota": "",
        "creado_por": "admin",
    }
    with pytest.raises(ErrorValidacion, match="fecha futura"):
        planes.registrar_aporte(
            plan_id, fecha_aporte=date.today() + timedelta(days=1),
            **datos,
        )
    with pytest.raises(ErrorValidacion, match="fuente"):
        planes.registrar_aporte(
            plan_id, fecha_aporte=date.today(), **datos
        )



def test_inversion_real_con_flujos_valuacion_y_xirr(repo):
    _, planes = repo
    plan_id = planes.guardar_snapshot(
        nombre="Cartera para reposición",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date.today() - timedelta(days=400),
        capital_original_ars=Decimal("12000000.00"),
        datos=_datos(),
        creado_por="admin",
    )
    fecha_inicio = date.today() - timedelta(days=365)
    flujo_id = planes.registrar_flujo_inversion(
        plan_id,
        fecha_flujo=fecha_inicio,
        tipo_flujo="APORTE_INVERSION",
        moneda="USD",
        monto_original=Decimal("1000.00"),
        naturaleza_cotizacion="NO_APLICA",
        creado_por="admin",
    )
    flujo = planes.obtener_flujo_inversion(flujo_id)
    assert flujo is not None
    assert flujo.equivalente_usd == Decimal("1000.00")
    assert planes.verificar_flujo_inversion(flujo)

    valoracion_id = planes.registrar_valoracion_inversion(
        plan_id,
        fecha_valuacion=date.today(),
        moneda="USD",
        valor_original=Decimal("1100.00"),
        naturaleza_cotizacion="NO_APLICA",
        referencia="Corte al cierre",
        creado_por="admin",
    )
    valoracion = planes.obtener_valoracion_inversion(valoracion_id)
    assert valoracion is not None
    assert valoracion.equivalente_usd == Decimal("1100.00")
    assert planes.verificar_valoracion_inversion(valoracion)

    resumen = planes.resumen_rendimiento_inversion(plan_id)
    assert resumen.cantidad_flujos == 1
    assert resumen.cantidad_valuaciones == 1
    assert resumen.aportes_inversion_usd_ref == Decimal("1000.00")
    assert resumen.valor_mercado_final_usd_ref == Decimal("1100.00")
    assert resumen.resultado_total_usd_ref == Decimal("100.00")
    assert resumen.xirr_anual == pytest.approx(Decimal("0.10"), abs=Decimal("0.005"))


def test_flujos_ars_convierten_usd_con_cotizacion_fechada(repo):
    _, planes = repo
    plan_id = planes.guardar_snapshot(
        nombre="Inversión en pesos",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date.today() - timedelta(days=30),
        capital_original_ars=Decimal("1000"),
        datos=_datos(),
        creado_por="admin",
    )
    flujo_id = planes.registrar_flujo_inversion(
        plan_id,
        fecha_flujo=date.today() - timedelta(days=1),
        tipo_flujo="APORTE_INVERSION",
        moneda="ARS",
        monto_original=Decimal("1500000.00"),
        cotizacion_ars_por_usd=Decimal("1500.000000"),
        naturaleza_cotizacion="OBSERVADA",
        fuente_cotizacion="Registro de prueba",
        creado_por="admin",
    )
    flujo = planes.obtener_flujo_inversion(flujo_id)
    assert flujo is not None
    assert flujo.equivalente_usd == Decimal("1000.00")
    assert flujo.naturaleza_cotizacion == "OBSERVADA"
    assert planes.verificar_flujo_inversion(flujo)


def test_rendimiento_no_se_calcula_sin_valuacion_final(repo):
    _, planes = repo
    plan_id = planes.guardar_snapshot(
        nombre="Cartera sin valuación",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date.today() - timedelta(days=30),
        capital_original_ars=Decimal("1000"),
        datos=_datos(),
        creado_por="admin",
    )
    planes.registrar_flujo_inversion(
        plan_id,
        fecha_flujo=date.today() - timedelta(days=1),
        tipo_flujo="APORTE_INVERSION",
        moneda="USD",
        monto_original=Decimal("100.00"),
        naturaleza_cotizacion="NO_APLICA",
        creado_por="admin",
    )
    resumen = planes.resumen_rendimiento_inversion(plan_id)
    assert resumen.xirr_anual is None
    assert resumen.resultado_total_usd_ref is None
    assert "valuación" in resumen.mensaje_xirr


def test_inversion_rechaza_cotizacion_observada_sin_fuente(repo):
    _, planes = repo
    plan_id = planes.guardar_snapshot(
        nombre="Cartera",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date.today() - timedelta(days=30),
        capital_original_ars=Decimal("1000"),
        datos=_datos(),
        creado_por="admin",
    )
    with pytest.raises(ErrorValidacion, match="fuente"):
        planes.registrar_flujo_inversion(
            plan_id,
            fecha_flujo=date.today(),
            tipo_flujo="APORTE_INVERSION",
            moneda="ARS",
            monto_original=Decimal("100.00"),
            cotizacion_ars_por_usd=Decimal("1000.00"),
            naturaleza_cotizacion="OBSERVADA",
            fuente_cotizacion="",
            creado_por="admin",
        )



def test_flujos_y_valuaciones_de_inversion_conservan_historial(repo):
    db, planes = repo
    plan_id = planes.guardar_snapshot(
        nombre="Cartera inmutable",
        tipo_plan="REPOSICION_INTERNA",
        fecha_desembolso=date.today() - timedelta(days=10),
        capital_original_ars=Decimal("1000"),
        datos=_datos(),
        creado_por="admin",
    )
    flujo_id = planes.registrar_flujo_inversion(
        plan_id,
        fecha_flujo=date.today() - timedelta(days=2),
        tipo_flujo="APORTE_INVERSION",
        moneda="USD",
        monto_original=Decimal("50.00"),
        naturaleza_cotizacion="NO_APLICA",
        creado_por="admin",
    )
    valoracion_id = planes.registrar_valoracion_inversion(
        plan_id,
        fecha_valuacion=date.today() - timedelta(days=1),
        moneda="USD",
        valor_original=Decimal("52.00"),
        naturaleza_cotizacion="NO_APLICA",
        creado_por="admin",
    )
    with pytest.raises(Exception, match="inmutables"):
        db.ejecutar(
            "UPDATE flujos_inversion_reposicion SET monto_original = '1' WHERE id = ?",
            (flujo_id,),
        )
    with pytest.raises(Exception, match="historial"):
        db.ejecutar(
            "DELETE FROM flujos_inversion_reposicion WHERE id = ?",
            (flujo_id,),
        )
    with pytest.raises(Exception, match="inmutables"):
        db.ejecutar(
            "UPDATE valuaciones_inversion_reposicion SET valor_original = '1' WHERE id = ?",
            (valoracion_id,),
        )
    with pytest.raises(Exception, match="historial"):
        db.ejecutar(
            "DELETE FROM valuaciones_inversion_reposicion WHERE id = ?",
            (valoracion_id,),
        )
