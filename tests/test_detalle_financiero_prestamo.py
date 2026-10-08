"""Pruebas del detalle financiero profundo de préstamos."""

from pathlib import Path

from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from aplicacion.consultas.detalle_financiero_prestamo import (
    DetalleFinancieroPrestamoQuery,
)


def _base(tmp_path: Path):
    db = BaseDatos(tmp_path / "detalle.db")
    db.abrir()
    aplicar_migraciones(db)

    db.ejecutar(
        "INSERT INTO personas (nombre, creado_en) VALUES ('Deudor', '2026-01-01')"
    )
    deudor = db.ultimo_id_insertado()
    db.ejecutar(
        """
        INSERT INTO prestamos
        (numero, deudor_id, moneda_contractual, capital_original, plazo_meses,
         sistema, convencion_dias, fecha_inicio, estado, creado_en)
        VALUES ('PR-K6', ?, 'ARS', '1000.00', 12, 'FRANCES', 'MENSUAL',
                '2026-01-01', 'ACTIVO', '2026-01-01')
        """,
        (deudor,),
    )
    prestamo = db.ultimo_id_insertado()
    db.ejecutar(
        """
        INSERT INTO versiones_tasa
        (prestamo_id, version, fecha_desde, tasa_anual, modalidad_tasa, creado_en)
        VALUES (?, 1, '2026-01-01', '0.24', 'TNA', '2026-01-01')
        """,
        (prestamo,),
    )
    version = db.ultimo_id_insertado()

    db.ejecutar(
        """
        INSERT INTO cuotas
        (version_id, numero, fecha_vencimiento, capital_inicial, interes,
         capital, cuota, saldo, monto_pendiente, interes_pendiente,
         capital_pendiente, mora_pendiente, fue_mora, tuvo_pago_parcial,
         fue_recalculada, estado, creado_en)
        VALUES (?, 1, '2026-02-01', '1000.00', '20.00', '80.00', '100.00',
                '920.00', '0.00', '0.00', '80.00', '0.00', 0, 0, 0,
                'PARCIAL', '2026-01-01')
        """,
        (version,),
    )
    db.ejecutar(
        """
        INSERT INTO cuotas
        (version_id, numero, fecha_vencimiento, capital_inicial, interes,
         capital, cuota, saldo, monto_pendiente, interes_pendiente,
         capital_pendiente, mora_pendiente, fue_mora, tuvo_pago_parcial,
         fue_recalculada, estado, creado_en)
        VALUES (?, 2, '2026-03-01', '920.00', '18.00', '82.00', '100.00',
                '838.00', '0.00', '0.00', '0.00', '0.00', 0, 0, 1,
                'PENDIENTE', '2026-01-01')
        """,
        (version,),
    )

    for fecha, monto in (("2026-02-01", "30.00"), ("2026-03-01", "82.00")):
        db.ejecutar(
            """
            INSERT INTO pagos
            (prestamo_id, fecha_real, fecha_valor, fecha_registro,
             monto_moneda_pago, monto_moneda_contractual, estado,
             creado_por, tipo_pago)
            VALUES (?, ?, ?, ?, ?, ?, 'VALIDA', 'test', 'CUOTA')
            """,
            (prestamo, fecha, fecha, fecha, monto, monto),
        )
        pago = db.ultimo_id_insertado()
        capital = "10.00" if monto == "30.00" else "72.00"
        db.ejecutar(
            """
            INSERT INTO imputaciones
            (pago_id, cuota_id, concepto, monto, creado_en, origen,
             referencias_devengamiento)
            VALUES (?, 1, 'CAPITAL', ?, ?, 'SALDO_CONTRACTUAL', '[]')
            """,
            (pago, capital, fecha),
        )

    db.ejecutar(
        """
        INSERT INTO devengamientos
        (prestamo_id, cuota_id, concepto, monto, fecha_desde, fecha_hasta,
         origen, referencia, base, tasa_anual, dias, fraccion_anual,
         huella, motor_version, creado_en)
        VALUES (?, 1, 'INTERES', '2.25', '2026-02-01', '2026-03-01',
                'TEST', 'DEV-1', '100.00', '0.24', 28, '0.0767',
                'k6-dev-1', 'V3-G3', '2026-03-01')
        """,
        (prestamo,),
    )
    return db, prestamo


def test_detalle_financiero_usa_decimal_y_fallback_contractual(tmp_path):
    db, prestamo = _base(tmp_path)
    try:
        detalle = DetalleFinancieroPrestamoQuery(db).obtener(prestamo)

        assert detalle.resumen.capital_original == 1000
        assert detalle.resumen.capital_aplicado == 82
        assert detalle.resumen.capital_pendiente == 162
        assert detalle.resumen.interes_devengado == 2.25
        assert len(detalle.eventos_capital) == 2
        assert detalle.eventos_capital[0].monto == 10
        assert detalle.eventos_capital[1].monto == 72

        cuota_2 = next(c for c in detalle.cuotas if c.numero == 2)
        assert cuota_2.fue_recalculada is True
        assert cuota_2.capital_pendiente == 82

        assert detalle.resumen.trayectoria.puntos[-1].capital == 918
    finally:
        db.cerrar()
