"""Pruebas del read model M7."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.consultas.comparador_decisiones_financieras import (
    ServicioComparadorDecisionesFinancieras,
)
from aplicacion.servicios.prestamos import ServicioPrestamos
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "m7.db"
    base = BaseDatos(ruta)
    base.abrir()
    aplicar_migraciones(base)
    yield base
    base.cerrar()


def _persona(db, nombre: str) -> int:
    return PersonaRepo(db).crear(nombre=nombre, apellido="M7")


def _crear_prestamo(
    db,
    *,
    deudor_id: int,
    inversor_id: int,
    numero: int,
    sistema: str = "FRANCES",
) -> int:
    capital = Decimal("1000.00") + Decimal(numero * 100)
    return ServicioPrestamos(db).crear_completo(
        deudor_id=deudor_id,
        capital=capital,
        plazo_meses=6,
        tasa_anual=Decimal("0.24"),
        modalidad_tasa="TNA",
        sistema=sistema,
        convencion_dias="MENSUAL",
        fecha_inicio=date(2026, 1, 1),
        inversores=[
            {"persona_id": inversor_id, "monto": capital},
        ],
        usuario="test-m7",
        tc_inicial=Decimal("1500.00"),
        destino=f"Alternativa {numero}",
    )


def _registrar_pago(db, prestamo_id: int, fecha: str, monto: str) -> None:
    db.ejecutar(
        """
        INSERT INTO pagos
        (prestamo_id, fecha_real, fecha_valor, fecha_registro,
         moneda_pago, monto_moneda_pago, monto_moneda_contractual,
         estado, creado_por, tipo_pago)
        VALUES (?, ?, ?, ?, 'ARS', ?, ?, 'VALIDA', 'test-m7', 'CUOTA')
        """,
        (prestamo_id, fecha, fecha, fecha, monto, monto),
    )


def test_lista_y_compara_dos_alternativas(db):
    persona = _persona(db, "Javier")
    inversor = _persona(db, "Inversor")

    primero = _crear_prestamo(
        db,
        deudor_id=persona,
        inversor_id=inversor,
        numero=1,
    )
    segundo = _crear_prestamo(
        db,
        deudor_id=persona,
        inversor_id=inversor,
        numero=2,
    )

    _registrar_pago(db, primero, "2026-02-01", "100.00")
    _registrar_pago(db, segundo, "2026-03-01", "150.00")

    servicio = ServicioComparadorDecisionesFinancieras(db)
    disponibles = servicio.listar_alternativas(persona)

    assert len(disponibles) == 2
    assert {item.prestamo_id for item in disponibles} == {primero, segundo}
    assert all(item.rol == "DEUDOR" for item in disponibles)

    resultado = servicio.comparar(
        persona,
        tuple(item.clave for item in disponibles),
        fecha_corte=date(2026, 4, 1),
        horizonte_meses=3,
        inflacion_mensual_supuesto=Decimal("0.05"),
    )

    assert resultado.cantidad_alternativas == 2
    assert resultado.homogenea
    assert resultado.inflacion_mensual_supuesto == Decimal("0.05")

    por_id = {item.prestamo_id: item for item in resultado.alternativas}
    assert por_id[primero].capital_referencia == Decimal("1100.00")
    assert por_id[segundo].capital_referencia == Decimal("1200.00")
    assert por_id[primero].flujo_real_neto > 0
    assert por_id[segundo].flujo_real_neto > 0
    assert por_id[primero].cantidad_flujos_futuros > 0
    assert por_id[segundo].cantidad_flujos_futuros > 0
    assert por_id[primero].valor_real_futuro < 0
    assert por_id[segundo].valor_real_futuro < 0


def test_advierte_cuando_las_reglas_no_son_homogeneas(db):
    persona = _persona(db, "Javier")
    inversor = _persona(db, "Inversor")

    primero = _crear_prestamo(
        db,
        deudor_id=persona,
        inversor_id=inversor,
        numero=1,
        sistema="FRANCES",
    )
    segundo = _crear_prestamo(
        db,
        deudor_id=persona,
        inversor_id=inversor,
        numero=2,
        sistema="ALEMAN",
    )

    servicio = ServicioComparadorDecisionesFinancieras(db)
    claves = tuple(
        item.clave
        for item in servicio.listar_alternativas(persona)
        if item.prestamo_id in {primero, segundo}
    )

    resultado = servicio.comparar(
        persona,
        claves,
        fecha_corte=date(2026, 1, 2),
        horizonte_meses=6,
    )

    assert not resultado.homogenea
    assert any(
        "sistemas de amortización diferentes" in motivo
        for motivo in resultado.motivos_no_homogeneidad
    )


def test_rechaza_menos_de_dos_alternativas(db):
    persona = _persona(db, "Javier")
    inversor = _persona(db, "Inversor")
    _crear_prestamo(
        db,
        deudor_id=persona,
        inversor_id=inversor,
        numero=1,
    )

    alternativa = ServicioComparadorDecisionesFinancieras(db).listar_alternativas(persona)[0]

    with pytest.raises(ValueError, match="al menos dos"):
        ServicioComparadorDecisionesFinancieras(db).comparar(
            persona,
            (alternativa.clave,),
        )
