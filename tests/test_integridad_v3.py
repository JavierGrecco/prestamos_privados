from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from infraestructura.consultas.integridad_v3 import auditar_integridad_v3, exigir_integridad_v3
from dominio.excepciones import ErrorValidacion


class DB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

    def ejecutar(self, sql, params=()):
        return self.conn.execute(sql, params)

    def consultar(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def consultar_uno(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()


def crear_db_sana() -> DB:
    db = DB()
    db.conn.executescript(
        """
        CREATE TABLE migraciones(version INTEGER PRIMARY KEY);
        INSERT INTO migraciones VALUES (10);
        CREATE TABLE prestamos(id INTEGER PRIMARY KEY, revision_prestamo INTEGER NOT NULL);
        CREATE TABLE pagos(
            id INTEGER PRIMARY KEY,
            prestamo_id INTEGER NOT NULL,
            monto_moneda_contractual TEXT NOT NULL,
            plan_hash TEXT,
            plan_json TEXT,
            motor_version TEXT NOT NULL,
            idempotency_key TEXT
        );
        CREATE TABLE imputaciones(
            id INTEGER PRIMARY KEY,
            pago_id INTEGER NOT NULL,
            cuota_id INTEGER,
            monto TEXT NOT NULL,
            referencias_devengamiento TEXT NOT NULL
        );
        CREATE TABLE cuotas(
            id INTEGER PRIMARY KEY,
            interes_pendiente TEXT NOT NULL,
            capital_pendiente TEXT NOT NULL,
            mora_pendiente TEXT NOT NULL,
            monto_pendiente TEXT NOT NULL,
            estado TEXT NOT NULL
        );
        CREATE TABLE ledger(
            id INTEGER PRIMARY KEY,
            entidad TEXT NOT NULL,
            entidad_id INTEGER NOT NULL,
            tipo_movimiento TEXT NOT NULL,
            debe TEXT NOT NULL,
            haber TEXT NOT NULL,
            metadata TEXT,
            correlacion_id TEXT NOT NULL
        );
        CREATE TABLE auditoria(
            id INTEGER PRIMARY KEY,
            entidad TEXT NOT NULL,
            entidad_id INTEGER,
            correlacion_id TEXT NOT NULL,
            operacion TEXT NOT NULL
        );
        CREATE TABLE devengamientos(
            id INTEGER PRIMARY KEY,
            prestamo_id INTEGER NOT NULL,
            cuota_id INTEGER,
            monto TEXT NOT NULL,
            fecha_desde TEXT NOT NULL,
            fecha_hasta TEXT NOT NULL,
            huella TEXT NOT NULL,
            referencia TEXT
        );
        """
    )
    db.ejecutar("INSERT INTO prestamos VALUES (1, 1)")
    db.ejecutar("INSERT INTO cuotas VALUES (1, '0', '80', '0', '80', 'PARCIAL')")
    plan_json = json.dumps({"monto": "100.00"}, separators=(",", ":"))
    plan_hash = hashlib.sha256(plan_json.encode("utf-8")).hexdigest()
    db.ejecutar(
        "INSERT INTO pagos VALUES (1, 1, '100.00', ?, ?, 'V3-G7', 'idem-1')",
        (plan_hash, plan_json),
    )
    db.ejecutar(
        "INSERT INTO imputaciones VALUES (1, 1, 1, '100.00', '[]')"
    )
    db.ejecutar(
        "INSERT INTO ledger VALUES (1, 'PAGO', 1, 'PAGO', '100', '0', '{\"pago_id\":1}', 'corr-1')"
    )
    db.ejecutar(
        "INSERT INTO ledger VALUES (2, 'PRESTAMO', 1, 'PAGO_RECIBIDO', '0', '100', '{\"pago_id\":1}', 'corr-1')"
    )
    db.ejecutar(
        "INSERT INTO auditoria VALUES (1, 'PAGO', 1, 'corr-1', 'PAGO_REGISTRADO_V3')"
    )
    db.conn.commit()
    return db


def test_base_sana_supera_el_gate():
    db = crear_db_sana()
    informe = auditar_integridad_v3(db)
    assert informe.ok
    assert informe.pagos_v3 == 1
    assert informe.imputaciones_v3 == 1
    exigir_integridad_v3(db)


def test_detecta_plan_hash_inconsistente():
    db = crear_db_sana()
    db.ejecutar("UPDATE pagos SET plan_hash='0' WHERE id=1")
    db.conn.commit()
    informe = auditar_integridad_v3(db)
    assert any(i.categoria == "PLAN" for i in informe.incidencias)


def test_detecta_imputacion_no_conservada():
    db = crear_db_sana()
    db.ejecutar("UPDATE imputaciones SET monto='99.99' WHERE id=1")
    db.conn.commit()
    informe = auditar_integridad_v3(db)
    assert any(i.categoria == "IMPUTACION" for i in informe.incidencias)


def test_detecta_ledger_desbalanceado():
    db = crear_db_sana()
    db.ejecutar("UPDATE ledger SET haber='90' WHERE id=2")
    db.conn.commit()
    informe = auditar_integridad_v3(db)
    assert any(i.categoria == "LEDGER" for i in informe.incidencias)


def test_detecta_correlacion_entre_ledger_y_auditoria():
    db = crear_db_sana()
    db.ejecutar("UPDATE auditoria SET correlacion_id='otra' WHERE id=1")
    db.conn.commit()
    informe = auditar_integridad_v3(db)
    assert any(i.categoria == "CORRELACION" for i in informe.incidencias)
    with pytest.raises(ErrorValidacion, match="auditoría de integridad V3"):
        exigir_integridad_v3(db)


def test_detecta_referencia_de_devengamiento_inexistente():
    db = crear_db_sana()
    db.ejecutar(
        "UPDATE imputaciones SET referencias_devengamiento=? WHERE id=1",
        (json.dumps(["ref-inexistente"]),),
    )
    db.conn.commit()
    informe = auditar_integridad_v3(db)
    assert any(i.categoria == "DEVENGAMIENTO_REF" for i in informe.incidencias)


def test_detecta_cuota_pagada_con_saldo():
    db = crear_db_sana()
    db.ejecutar("UPDATE cuotas SET estado='PAGADA' WHERE id=1")
    db.conn.commit()
    informe = auditar_integridad_v3(db)
    assert any(i.categoria == "CUOTA" for i in informe.incidencias)


def test_auditoria_es_solo_lectura():
    db = crear_db_sana()
    antes = db.consultar_uno(
        "SELECT COUNT(*) AS n FROM pagos"
    )["n"]
    snapshot = db.consultar(
        "SELECT id, plan_hash, plan_json FROM pagos ORDER BY id"
    )
    auditar_integridad_v3(db)
    despues = db.consultar_uno(
        "SELECT COUNT(*) AS n FROM pagos"
    )["n"]
    snapshot_despues = db.consultar(
        "SELECT id, plan_hash, plan_json FROM pagos ORDER BY id"
    )
    assert antes == despues == 1
    assert snapshot == snapshot_despues


def test_detecta_metadata_ledger_invalida_sin_abortar():
    db = crear_db_sana()
    db.ejecutar("UPDATE ledger SET metadata='NO-JSON' WHERE id=2")
    db.conn.commit()
    informe = auditar_integridad_v3(db)
    assert any(i.categoria == "LEDGER_METADATA" for i in informe.incidencias)
