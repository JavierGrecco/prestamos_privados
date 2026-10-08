"""Pruebas del read model financiero K2."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.consultas.analisis_financiero import AnalisisFinancieroQuery
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "k2.db"
    base = BaseDatos(ruta)
    base.abrir()
    aplicar_migraciones(base)
    yield base
    base.cerrar()


def _crear_persona(db, nombre: str) -> int:
    db.ejecutar(
        "INSERT INTO personas (nombre, creado_en) VALUES (?, ?)",
        (nombre, "2026-01-01"),
    )
    return db.ultimo_id_insertado()


def _crear_prestamo(
    db,
    *,
    deudor_id: int,
    inversor_id: int,
    capital: str = "1000.00",
) -> int:
    db.ejecutar(
        """
        INSERT INTO prestamos
        (numero, deudor_id, moneda_contractual, capital_original, plazo_meses,
         sistema, convencion_dias, fecha_inicio, estado, creado_en)
        VALUES (?, ?, 'ARS', ?, 12, 'FRANCES', 'MENSUAL', '2026-01-01',
                'ACTIVO', '2026-01-01')
        """,
        ("PR-K2", deudor_id, capital),
    )
    prestamo_id = db.ultimo_id_insertado()

    db.ejecutar(
        """
        INSERT INTO versiones_tasa
        (prestamo_id, version, fecha_desde, tasa_anual, modalidad_tasa, creado_en)
        VALUES (?, 1, '2026-01-01', '0.10', 'TNA', '2026-01-01')
        """,
        (prestamo_id,),
    )
    version_id = db.ultimo_id_insertado()

    db.ejecutar(
        """
        INSERT INTO cuotas
        (version_id, numero, fecha_vencimiento, capital_inicial, interes,
         capital, cuota, saldo, monto_pendiente, interes_pendiente,
         capital_pendiente, mora_pendiente, fue_mora, tuvo_pago_parcial,
         fue_recalculada, estado, creado_en)
        VALUES (?, 1, '2027-01-01', '1000.00', '0.00', '1000.00', '1100.00',
                '0.00', '0.00', '0.00', '1000.00', '0.00', 0, 0, 0,
                'PENDIENTE', '2026-01-01')
        """,
        (version_id,),
    )

    db.ejecutar(
        """
        INSERT INTO participaciones
        (prestamo_id, inversor_id, capital_aportado, moneda_aporte,
         tc_aporte, capital_usd_ref, porcentaje, fecha_aporte, estado, creado_en)
        VALUES (?, ?, '1000.00', 'ARS', '1000.00', '1.00', '1.00',
                '2026-01-01', 'ACTIVA', '2026-01-01')
        """,
        (prestamo_id, inversor_id),
    )

    return prestamo_id


def test_inversor_tiene_cashflow_real_y_xirr(db):
    persona = _crear_persona(db, "Inversor")
    deudor = _crear_persona(db, "Deudor")
    prestamo = _crear_prestamo(
        db,
        deudor_id=deudor,
        inversor_id=persona,
    )

    db.ejecutar(
        """
        INSERT INTO pagos
        (prestamo_id, fecha_real, fecha_valor, fecha_registro,
         moneda_pago, monto_moneda_pago, monto_moneda_contractual,
         estado, creado_por, tipo_pago)
        VALUES (?, '2027-01-01', '2027-01-01', '2027-01-01',
                'ARS', '1100.00', '1100.00', 'VALIDA', 'test', 'CUOTA')
        """,
        (prestamo,),
    )
    pago_id = db.ultimo_id_insertado()

    db.ejecutar(
        """
        INSERT INTO ledger
        (entidad, entidad_id, tipo_movimiento, debe, haber, fecha,
         metadata, correlacion_id, creado_en)
        VALUES ('INVERSOR', ?, 'COBRO_PAGO', '1100.00', '0.00',
                '2027-01-01', ?, 'k2-test', '2027-01-01')
        """,
        (persona, '{"pago_id": %d}' % pago_id),
    )

    resultado = AnalisisFinancieroQuery(db).obtener(
        persona,
        fecha_corte=date(2027, 1, 2),
        inflacion_mensual_supuesto=Decimal("0.00"),
    )

    tipos = [(f.tipo, f.monto_ars) for f in resultado.flujos_reales]
    assert ("APORTE", Decimal("-1000.00")) in tipos
    assert ("COBRO", Decimal("1100.00")) in tipos
    assert resultado.resumen.xirr_inversor == Decimal("0.10000000")
    assert resultado.resumen.rendimiento_real_inversor == Decimal("0.10000000")
    assert resultado.resumen.capital_aportado_activo == Decimal("1000.00")


def test_deudor_tiene_desembolso_pago_y_capital_pendiente(db):
    persona = _crear_persona(db, "Deudor")
    inversor = _crear_persona(db, "Inversor")
    prestamo = _crear_prestamo(
        db,
        deudor_id=persona,
        inversor_id=inversor,
    )

    db.ejecutar(
        """
        INSERT INTO pagos
        (prestamo_id, fecha_real, fecha_valor, fecha_registro,
         moneda_pago, monto_moneda_pago, monto_moneda_contractual,
         estado, creado_por, tipo_pago)
        VALUES (?, '2026-06-01', '2026-06-01', '2026-06-01',
                'ARS', '100.00', '100.00', 'VALIDA', 'test', 'CUOTA')
        """,
        (prestamo,),
    )

    resultado = AnalisisFinancieroQuery(db).obtener(
        persona,
        fecha_corte=date(2026, 6, 2),
        inflacion_mensual_supuesto=Decimal("0.05"),
    )

    assert resultado.resumen.capital_deudor_pendiente == Decimal("1000.00")
    assert resultado.resumen.pagos_deudor_reales == Decimal("100.00")
    assert any(f.tipo == "DESEMBOLSO" and f.monto_ars == Decimal("1000.00")
               for f in resultado.flujos_reales)
    assert any(f.tipo == "PAGO" and f.monto_ars == Decimal("-100.00")
               for f in resultado.flujos_reales)
    assert len(resultado.flujos_proyectados) == 1
    assert resultado.flujos_proyectados[0].monto_ars == Decimal("-1000.00")


def test_escenarios_usan_el_motor_existente(db):
    persona = _crear_persona(db, "Deudor")
    inversor = _crear_persona(db, "Inversor")
    prestamo = _crear_prestamo(
        db,
        deudor_id=persona,
        inversor_id=inversor,
    )

    resultado = AnalisisFinancieroQuery(db).escenarios_para_prestamo(prestamo)

    assert len(resultado.resultados) == 4
    assert [x.escenario.nombre for x in resultado.resultados] == [
        "Optimista",
        "Base",
        "Pesimista",
        "Crisis",
    ]
    assert all(x.cuota_final_real > 0 for x in resultado.resultados)


def test_no_inventa_dolar_futuro_en_proyeccion(db):
    persona = _crear_persona(db, "Inversor")
    deudor = _crear_persona(db, "Deudor")
    _crear_prestamo(
        db,
        deudor_id=deudor,
        inversor_id=persona,
    )

    resultado = AnalisisFinancieroQuery(db).obtener(
        persona,
        fecha_corte=date(2026, 1, 2),
    )

    assert resultado.flujos_proyectados
    assert all(f.monto_usd is None for f in resultado.flujos_proyectados)
