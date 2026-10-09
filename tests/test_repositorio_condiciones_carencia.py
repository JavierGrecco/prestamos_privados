"""Pruebas de persistencia inmutable para condiciones de carencia."""
from datetime import date
from decimal import Decimal

import pytest

from dominio import (
    ConvencionDias,
    ErrorValidacion,
    ModalidadTasa,
    SistemaAmortizacion,
    crear_condiciones_carencia,
)
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import (
    CondicionesCarenciaRepo,
    PersonaRepo,
    PrestamoRepo,
)


@pytest.fixture
def contrato_base(tmp_path):
    ruta = tmp_path / "contrato-carencia.db"
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        prestamos = PrestamoRepo(db)
        deudor_id = personas.crear(nombre="Deudor")
        prestamo_id = prestamos.crear(
            deudor_id=deudor_id,
            capital_original=Decimal("1000000.00"),
            plazo_meses=24,
            sistema="FRANCES",
            convencion_dias="MENSUAL",
            fecha_inicio=date(2026, 1, 31),
        )
        version_tasa_id = prestamos.crear_version_tasa(
            prestamo_id=prestamo_id,
            tasa_anual=Decimal("0.36"),
            modalidad_tasa="TNA",
            fecha_desde=date(2026, 1, 31),
        )
        condiciones = crear_condiciones_carencia(
            capital_original=Decimal("1000000.00"),
            tasa_anual=Decimal("0.36"),
            modalidad_tasa=ModalidadTasa.TNA,
            convencion_dias=ConvencionDias.MENSUAL,
            sistema=SistemaAmortizacion.FRANCES,
            meses_carencia=12,
            fecha_desembolso=date(2026, 1, 31),
            plazo_amortizacion_meses=24,
            tratamiento="DIFERIR_SIMPLE_DISTRIBUIDO",
        )
        yield db, prestamo_id, version_tasa_id, condiciones


def test_guarda_y_recupera_snapshot_canónico_verificable(contrato_base):
    db, prestamo_id, version_tasa_id, condiciones = contrato_base
    repo = CondicionesCarenciaRepo(db)

    snapshot_id = repo.guardar_snapshot(
        prestamo_id=prestamo_id,
        version_tasa_id=version_tasa_id,
        condiciones=condiciones,
        creado_por="admin",
    )
    snapshot = repo.obtener_actual(prestamo_id)

    assert snapshot is not None
    assert snapshot.id == snapshot_id
    assert snapshot.version_contrato == 1
    assert snapshot.version_tasa_id == version_tasa_id
    assert snapshot.tratamiento == "DIFERIR_SIMPLE_DISTRIBUIDO"
    assert snapshot.interes_carencia_debido == Decimal("360000.00")
    assert snapshot.interes_carencia_no_cobrado == Decimal("0.00")
    assert snapshot.fecha_fin_carencia == date(2027, 1, 31)
    assert snapshot.fecha_primer_vencimiento == date(2027, 2, 28)
    assert repo.verificar_snapshot(snapshot)
    assert len(repo.listar_versiones(prestamo_id)) == 1


def test_snapshot_es_append_only_no_admite_update_ni_delete(contrato_base):
    db, prestamo_id, version_tasa_id, condiciones = contrato_base
    repo = CondicionesCarenciaRepo(db)
    snapshot_id = repo.guardar_snapshot(
        prestamo_id=prestamo_id,
        version_tasa_id=version_tasa_id,
        condiciones=condiciones,
        creado_por="admin",
    )

    with pytest.raises(Exception, match="inmutable"):
        db.ejecutar(
            "UPDATE condiciones_carencia SET tratamiento = 'SIN_INTERES' WHERE id = ?",
            (snapshot_id,),
        )
    with pytest.raises(Exception, match="inmutable"):
        db.ejecutar(
            "DELETE FROM condiciones_carencia WHERE id = ?",
            (snapshot_id,),
        )


def test_nueva_version_agrega_un_snapshot_sin_reescribir_el_anterior(contrato_base):
    db, prestamo_id, version_tasa_id, condiciones = contrato_base
    repo = CondicionesCarenciaRepo(db)

    primero = repo.guardar_snapshot(
        prestamo_id=prestamo_id,
        version_tasa_id=version_tasa_id,
        condiciones=condiciones,
        creado_por="admin",
    )
    segundo = repo.guardar_snapshot(
        prestamo_id=prestamo_id,
        version_tasa_id=version_tasa_id,
        condiciones=condiciones,
        creado_por="admin",
    )
    versiones = repo.listar_versiones(prestamo_id)

    assert segundo != primero
    assert [s.version_contrato for s in versiones] == [1, 2]
    assert all(repo.verificar_snapshot(s) for s in versiones)
    assert versiones[0].snapshot_sha256 != versiones[1].snapshot_sha256


def test_rechaza_snapshot_que_no_coincide_con_prestamo(contrato_base):
    db, prestamo_id, version_tasa_id, condiciones = contrato_base
    repo = CondicionesCarenciaRepo(db)
    condiciones_incorrectas = crear_condiciones_carencia(
        capital_original=Decimal("900000.00"),
        tasa_anual=Decimal("0.36"),
        modalidad_tasa=ModalidadTasa.TNA,
        convencion_dias=ConvencionDias.MENSUAL,
        sistema=SistemaAmortizacion.FRANCES,
        meses_carencia=12,
        fecha_desembolso=date(2026, 1, 31),
        plazo_amortizacion_meses=24,
        tratamiento="DIFERIR_SIMPLE_DISTRIBUIDO",
    )

    with pytest.raises(ErrorValidacion, match="capital del snapshot"):
        repo.guardar_snapshot(
            prestamo_id=prestamo_id,
            version_tasa_id=version_tasa_id,
            condiciones=condiciones_incorrectas,
            creado_por="admin",
        )
    assert repo.listar_versiones(prestamo_id) == []


def test_rechaza_version_de_tasa_de_otro_prestamo(contrato_base):
    db, prestamo_id, version_tasa_id, condiciones = contrato_base
    personas = PersonaRepo(db)
    prestamos = PrestamoRepo(db)
    otro_deudor = personas.crear(nombre="Otro")
    otro_prestamo = prestamos.crear(
        deudor_id=otro_deudor,
        capital_original=Decimal("1000000.00"),
        plazo_meses=24,
        sistema="FRANCES",
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 31),
    )
    otra_version = prestamos.crear_version_tasa(
        prestamo_id=otro_prestamo,
        tasa_anual=Decimal("0.36"),
        modalidad_tasa="TNA",
        fecha_desde=date(2026, 1, 31),
    )

    with pytest.raises(ErrorValidacion, match="no pertenece al préstamo"):
        CondicionesCarenciaRepo(db).guardar_snapshot(
            prestamo_id=prestamo_id,
            version_tasa_id=otra_version,
            condiciones=condiciones,
            creado_por="admin",
        )


def test_rechaza_version_si_tasa_no_coincide_con_snapshot(contrato_base):
    db, prestamo_id, version_tasa_id, _ = contrato_base
    condiciones = crear_condiciones_carencia(
        capital_original=Decimal("1000000.00"),
        tasa_anual=Decimal("0.30"),
        modalidad_tasa=ModalidadTasa.TNA,
        convencion_dias=ConvencionDias.MENSUAL,
        sistema=SistemaAmortizacion.FRANCES,
        meses_carencia=12,
        fecha_desembolso=date(2026, 1, 31),
        plazo_amortizacion_meses=24,
        tratamiento="DIFERIR_SIMPLE_DISTRIBUIDO",
    )

    with pytest.raises(ErrorValidacion, match="tasa anual no coincide"):
        CondicionesCarenciaRepo(db).guardar_snapshot(
            prestamo_id=prestamo_id,
            version_tasa_id=version_tasa_id,
            condiciones=condiciones,
            creado_por="admin",
        )
