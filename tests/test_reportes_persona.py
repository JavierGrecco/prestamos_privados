"""Pruebas de reportes financieros por persona."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from aplicacion.servicios.reportes_persona import ServicioReportesPersona
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.repositorios import PersonaRepo


def _crear_persona(personas, nombre, apellido, documento, rol):
    persona_id = personas.crear(
        nombre=nombre,
        apellido=apellido,
        documento=documento,
    )
    personas.agregar_rol(persona_id, rol)
    return persona_id


def _crear_contexto(db):
    personas = PersonaRepo(db)
    inversor = _crear_persona(personas, 'Lucía', 'Reporte', '99994001', 'INVERSOR')
    deudor = _crear_persona(personas, 'Carlos', 'Reporte', '99994002', 'DEUDOR')

    db.ejecutar(
        """
        INSERT INTO prestamos
        (numero, deudor_id, moneda_contractual, capital_original, plazo_meses,
         sistema, convencion_dias, fecha_inicio, estado, creado_en)
        VALUES ('PR-M6', ?, 'ARS', '1000.00', 6, 'FRANCES', 'MENSUAL',
                '2026-01-01', 'ACTIVO', '2026-01-01')
        """,
        (deudor,),
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
        (prestamo_id, inversor),
    )

    db.ejecutar(
        """
        INSERT INTO pagos
        (prestamo_id, fecha_real, fecha_valor, fecha_registro, moneda_pago,
         monto_moneda_pago, monto_moneda_contractual, monto_usd_ref, estado,
         creado_por, tipo_pago)
        VALUES (?, '2027-01-01', '2027-01-01', '2027-01-01', 'ARS',
                '1100.00', '1100.00', '1.10', 'VALIDA', 'test', 'CUOTA')
        """,
        (prestamo_id,),
    )
    pago_id = db.ultimo_id_insertado()
    db.ejecutar(
        """
        INSERT INTO ledger
        (entidad, entidad_id, tipo_movimiento, debe, haber, fecha,
         metadata, correlacion_id, creado_en)
        VALUES ('INVERSOR', ?, 'COBRO_PAGO', '1100.00', '0.00',
                '2027-01-01', ?, 'm6-test', '2027-01-01')
        """,
        (inversor, '{"pago_id": ' + str(pago_id) + '}'),
    )
    return inversor


def test_reporte_consolida_las_cuatro_capas_y_conserva_el_corte(tmp_path: Path):
    ruta = tmp_path / 'reporte.db'
    with BaseDatos(ruta) as db:
        aplicar_migraciones(db)
        inversor = _crear_contexto(db)
        servicio = ServicioReportesPersona(db)
        antes = db.consultar_uno('SELECT COUNT(*) n FROM auditoria')['n']

        reporte = servicio.obtener(
            inversor,
            fecha_corte=date(2027, 1, 2),
            inflacion_mensual_supuesto=Decimal('0.00'),
            horizonte_meses=6,
        )
        markdown = servicio.markdown(reporte)
        payload = servicio.json(reporte)
        csv = servicio.csv_resumen(reporte)

        despues = db.consultar_uno('SELECT COUNT(*) n FROM auditoria')['n']

    assert reporte.nombre == 'Lucía Reporte'
    assert reporte.fecha_corte == date(2027, 1, 2)
    assert reporte.horizonte_meses == 6
    assert reporte.posicion.capital_invertido == Decimal('1000.00')
    assert reporte.rendimiento.inversor is not None
    assert reporte.rendimiento.inversor.valor == Decimal('0.10000000')
    assert reporte.planificacion.horizonte_meses == 6
    assert len(reporte.escenarios.resultados) >= 4
    assert '# Reporte financiero' in markdown
    assert '## Posición conocida' in markdown
    assert '## Plan futuro' in markdown
    assert '## Rendimiento histórico' in markdown
    assert '## Escenarios' in markdown
    assert 'fecha_corte' in payload
    assert 'posicion' in payload
    assert 'planificacion' in payload
    assert 'rendimiento' in payload
    assert 'escenarios' in payload
    assert csv.startswith('seccion,indicador,valor,naturaleza')
    assert 'Capital invertido' in csv
    assert 'Rendimiento anualizado' in csv
    assert 'Sin asesoramiento financiero' not in markdown
    assert despues == antes