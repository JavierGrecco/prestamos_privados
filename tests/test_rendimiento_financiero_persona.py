"""Pruebas del rendimiento explicado para personas."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.consultas.rendimiento_financiero_persona import (
    ServicioRendimientoFinancieroPersona,
)
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


def _crear_prestamo(db, deudor_id: int, inversor_id: int) -> int:
    db.ejecutar(
        """
        INSERT INTO prestamos
        (numero, deudor_id, moneda_contractual, capital_original, plazo_meses,
         sistema, convencion_dias, fecha_inicio, estado, creado_en)
        VALUES ('PR-M5', ?, 'ARS', '1000.00', 12, 'FRANCES', 'MENSUAL',
                '2026-01-01', 'ACTIVO', '2026-01-01')
        """,
        (deudor_id,),
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
                '0.00', '1100.00', '0.00', '1000.00', '0.00', 0, 0, 0,
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


def _insertar_pago_y_cobro(db, prestamo_id: int, inversor_id: int, usd: str | None = None) -> None:
    monto_usd = 'NULL' if usd is None else f"'{usd}'"
    db.ejecutar(
        f"""
        INSERT INTO pagos
        (prestamo_id, fecha_real, fecha_valor, fecha_registro, moneda_pago,
         monto_moneda_pago, monto_moneda_contractual, monto_usd_ref, estado,
         creado_por, tipo_pago)
        VALUES (?, '2027-01-01', '2027-01-01', '2027-01-01', 'ARS',
                '1100.00', '1100.00', {monto_usd}, 'VALIDA', 'test', 'CUOTA')
        """
        , (prestamo_id,)
    )
    pago_id = db.ultimo_id_insertado()
    db.ejecutar(
        """
        INSERT INTO ledger
        (entidad, entidad_id, tipo_movimiento, debe, haber, fecha,
         metadata, correlacion_id, creado_en)
        VALUES ('INVERSOR', ?, 'COBRO_PAGO', '1100.00', '0.00',
                '2027-01-01', ?, 'm5-test', '2027-01-01')
        """,
        (inversor_id, '{"pago_id": ' + str(pago_id) + '}'),
    )


def test_rendimiento_inversor_disponible_y_explicado(tmp_path: Path):
    ruta = tmp_path / 'rendimiento.db'
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        inversor = personas.crear(nombre='Inversor', apellido='M5', documento='99993001')
        personas.agregar_rol(inversor, 'INVERSOR')
        deudor = personas.crear(nombre='Deudor', apellido='M5', documento='99993002')
        personas.agregar_rol(deudor, 'DEUDOR')
        prestamo = _crear_prestamo(db, deudor, inversor)
        _insertar_pago_y_cobro(db, prestamo, inversor, usd='1.10')

        resultado = ServicioRendimientoFinancieroPersona(db).obtener(
            inversor,
            fecha_corte=date(2027, 1, 2),
            inflacion_mensual_supuesto=Decimal('0.00'),
        )

    assert resultado.inversor is not None
    assert resultado.inversor.disponible
    assert resultado.inversor.valor == Decimal('0.10000000')
    assert resultado.inversor.valor_usd == Decimal('0.10000000')
    assert resultado.inversor.rendimiento_real == Decimal('0.10000000')
    assert resultado.inversor.evidencia_completa
    assert resultado.inversor.cantidad_flujos_reales == 2


def test_rendimiento_deudor_disponible_con_dos_flujos(tmp_path: Path):
    ruta = tmp_path / 'rendimiento_deudor.db'
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        deudor = personas.crear(nombre='Deudor', apellido='M5', documento='99993003')
        personas.agregar_rol(deudor, 'DEUDOR')
        inversor = personas.crear(nombre='Inversor', apellido='M5', documento='99993004')
        personas.agregar_rol(inversor, 'INVERSOR')
        prestamo = _crear_prestamo(db, deudor, inversor)
        db.ejecutar(
            """
            INSERT INTO pagos
            (prestamo_id, fecha_real, fecha_valor, fecha_registro, moneda_pago,
             monto_moneda_pago, monto_moneda_contractual, estado, creado_por, tipo_pago)
            VALUES (?, '2027-01-01', '2027-01-01', '2027-01-01', 'ARS',
                    '1100.00', '1100.00', 'VALIDA', 'test', 'CUOTA')
            """,
            (prestamo,),
        )

        resultado = ServicioRendimientoFinancieroPersona(db).obtener(
            deudor,
            fecha_corte=date(2027, 1, 2),
            inflacion_mensual_supuesto=Decimal('0.00'),
        )

    assert resultado.deudor is not None
    assert resultado.deudor.disponible
    assert resultado.deudor.valor == Decimal('0.10000000')
    assert resultado.deudor.evidencia_completa


def test_rendimiento_no_muestra_tasa_sin_cobro_o_pago_opuesto(tmp_path: Path):
    ruta = tmp_path / 'rendimiento_incompleto.db'
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        personas = PersonaRepo(db)
        inversor = personas.crear(nombre='Inversor', apellido='M5', documento='99993005')
        personas.agregar_rol(inversor, 'INVERSOR')
        deudor = personas.crear(nombre='Deudor', apellido='M5', documento='99993006')
        personas.agregar_rol(deudor, 'DEUDOR')
        _crear_prestamo(db, deudor, inversor)

        resultado = ServicioRendimientoFinancieroPersona(db).obtener(
            inversor,
            fecha_corte=date(2026, 10, 8),
        )

    assert resultado.inversor is not None
    assert not resultado.inversor.disponible
    assert resultado.inversor.valor is None
    assert 'no hay suficientes flujos reales' in resultado.inversor.explicacion.lower()