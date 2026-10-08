"""Pruebas del historial auditable de pagos."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion.consultas.historial_pagos import HistorialPagosQuery
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones


@pytest.fixture
def db(tmp_path: Path):
    ruta = tmp_path / "historial.db"
    db = BaseDatos(ruta)
    db.abrir()
    aplicar_migraciones(db)

    db.ejecutar(
        "INSERT INTO personas (nombre, creado_en) VALUES ('Deudor', '2026-01-01')"
    )
    deudor = db.ultimo_id_insertado()
    db.ejecutar(
        "INSERT INTO personas (nombre, creado_en) VALUES ('Inversor', '2026-01-01')"
    )
    inversor = db.ultimo_id_insertado()

    db.ejecutar(
        """
        INSERT INTO prestamos
        (numero, deudor_id, moneda_contractual, capital_original, plazo_meses,
         sistema, convencion_dias, fecha_inicio, estado, creado_en)
        VALUES ('PR-AUDIT', ?, 'ARS', '1000.00', 12, 'FRANCES', 'MENSUAL',
                '2026-01-01', 'ACTIVO', '2026-01-01')
        """,
        (deudor,),
    )
    prestamo = db.ultimo_id_insertado()

    db.ejecutar(
        """
        INSERT INTO participaciones
        (prestamo_id, inversor_id, capital_aportado, moneda_aporte,
         porcentaje, fecha_aporte, estado, creado_en)
        VALUES (?, ?, '1000.00', 'ARS', '1.00', '2026-01-01',
                'ACTIVA', '2026-01-01')
        """,
        (prestamo, inversor),
    )

    db.ejecutar(
        """
        INSERT INTO pagos
        (prestamo_id, fecha_real, fecha_valor, fecha_registro,
         moneda_pago, monto_moneda_pago, monto_moneda_contractual,
         estado, creado_por, tipo_pago, monto_a_capital, motor_version,
         plan_hash, plan_json, idempotency_key, idempotency_fingerprint)
        VALUES (?, '2026-02-01', '2026-02-01', '2026-02-01',
                'ARS', '100.00', '100.00', 'VALIDA', 'test', 'CUOTA',
                '80.00', 'V3-F3.1', 'hash-plan',
                '{"monto_pago_recibido":"100.00","tipo":"CUOTA"}',
                'audit-1', 'fingerprint-1')
        """,
        (prestamo,),
    )
    pago = db.ultimo_id_insertado()

    db.ejecutar(
        """
        INSERT INTO imputaciones
        (pago_id, cuota_id, concepto, monto, creado_en, origen,
         referencias_devengamiento)
        VALUES (?, NULL, 'CAPITAL', '100.00', '2026-02-01',
                'SALDO_CONTRACTUAL', '[]')
        """,
        (pago,),
    )

    db.ejecutar(
        """
        INSERT INTO ledger
        (entidad, entidad_id, tipo_movimiento, debe, haber, fecha,
         metadata, correlacion_id, creado_en)
        VALUES
        ('PRESTAMO', ?, 'PAGO_RECIBIDO', '0.00', '100.00', '2026-02-01',
         '{"pago_id": 1}', 'corr-1', '2026-02-01'),
        ('PAGO', ?, 'PAGO', '100.00', '0.00', '2026-02-01',
         '{"prestamo_id": 1}', 'corr-1', '2026-02-01')
        """,
        (prestamo, pago),
    )

    db.ejecutar(
        """
        INSERT INTO auditoria
        (fecha, usuario, operacion, entidad, entidad_id,
         datos_anteriores, datos_nuevos, motivo, correlacion_id)
        VALUES ('2026-02-01', 'test', 'PAGO_REGISTRADO_V3', 'PAGO', ?,
                NULL, '{}', 'prueba', 'corr-1')
        """,
        (pago,),
    )

    db.ejecutar(
        """
        INSERT INTO observaciones_sombra_v3
        (prestamo_id, pago_legacy_id, fingerprint, tipo, resumen,
         detalle_json, correlacion_id, motor_version, creado_en)
        VALUES (?, ?, 'fingerprint-1', 'SIN_DIVERGENCIA',
                'Coincide', '{}', 'corr-1', 'V3-SOMBRA', '2026-02-01')
        """,
        (prestamo, pago),
    )
    return db, deudor, inversor, prestamo, pago


def test_historial_por_persona_incluye_pago(db):
    base, deudor, _, _, pago_id = db
    try:
        pagos = HistorialPagosQuery(base).por_persona(deudor)
        assert [p.id for p in pagos] == [pago_id]
        assert pagos[0].motor_version == "V3-F3.1"
        assert pagos[0].idempotency_key == "audit-1"
    finally:
        base.cerrar()


def test_detalle_reconstruye_plan_ledger_auditoria_y_sombra(db):
    base, _, _, _, pago_id = db
    try:
        evidencia = HistorialPagosQuery(base).detalle(pago_id)

        assert evidencia is not None
        assert evidencia.pago.id == pago_id
        assert evidencia.pago.plan_hash == "hash-plan"
        assert evidencia.plan["tipo"] == "CUOTA"
        assert len(evidencia.imputaciones) == 1
        assert len(evidencia.ledger) == 2
        assert evidencia.correlacion_id == "corr-1"
        assert len(evidencia.auditoria) == 1
        assert len(evidencia.observaciones_sombra) == 1
        assert evidencia.observaciones_sombra[0]["tipo"] == "SIN_DIVERGENCIA"
    finally:
        base.cerrar()


def test_limite_se_ajusta_y_no_modifica_datos(db):
    base, deudor, _, _, _ = db
    try:
        with pytest.raises(ValueError):
            HistorialPagosQuery(base).por_persona(deudor, limite=0)

        assert HistorialPagosQuery(base).por_persona(deudor, limite=999)[0].id > 0
    finally:
        base.cerrar()
