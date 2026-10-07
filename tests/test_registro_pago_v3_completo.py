from datetime import date
from decimal import Decimal
import sqlite3

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.fabrica_registro_pago_v3 import crear_registrador_pago_v3_completo
from dominio.excepciones import ErrorInvariante
from dominio.tipos import ConvencionDias, ModalidadTasa
from infraestructura.migraciones.v010_devengamientos_v3 import aplicar


class DB:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON')
    @property
    def conexion(self): return self.conn
    def ejecutar(self, sql, params=()): return self.conn.execute(sql, params)
    def consultar(self, sql, params=()): return self.conn.execute(sql, params).fetchall()
    def consultar_uno(self, sql, params=()): return self.conn.execute(sql, params).fetchone()
    def ultimo_id_insertado(self): return self.conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    def close(self): self.conn.close()


def setup(db):
    db.conn.executescript('''
    CREATE TABLE personas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, creado_en TEXT NOT NULL);
    CREATE TABLE prestamos (
      id INTEGER PRIMARY KEY AUTOINCREMENT, numero TEXT UNIQUE NOT NULL,
      deudor_id INTEGER NOT NULL, moneda_contractual TEXT NOT NULL DEFAULT 'ARS', capital_original TEXT NOT NULL,
      plazo_meses INTEGER NOT NULL, sistema TEXT NOT NULL, convencion_dias TEXT NOT NULL,
      tc_inicial TEXT, fecha_inicio TEXT NOT NULL, fecha_fin_estimada TEXT,
      estado TEXT NOT NULL DEFAULT 'ACTIVO', destino TEXT, descripcion TEXT, creado_en TEXT NOT NULL, actualizado_en TEXT,
      revision_prestamo INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE versiones_tasa (
      id INTEGER PRIMARY KEY AUTOINCREMENT, prestamo_id INTEGER NOT NULL, version INTEGER NOT NULL,
      fecha_desde TEXT NOT NULL, fecha_hasta TEXT, tasa_anual TEXT NOT NULL, modalidad_tasa TEXT NOT NULL,
      motivo TEXT, creado_por TEXT, creado_en TEXT NOT NULL
    );
    CREATE TABLE cuotas (
      id INTEGER PRIMARY KEY AUTOINCREMENT, version_id INTEGER NOT NULL, numero INTEGER NOT NULL,
      fecha_vencimiento TEXT NOT NULL, capital_inicial TEXT NOT NULL, interes TEXT NOT NULL, capital TEXT NOT NULL,
      cuota TEXT NOT NULL, saldo TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'PENDIENTE', creado_en TEXT NOT NULL,
      monto_pendiente TEXT NOT NULL DEFAULT '0', interes_pendiente TEXT NOT NULL DEFAULT '0',
      capital_pendiente TEXT NOT NULL DEFAULT '0', mora_pendiente TEXT NOT NULL DEFAULT '0',
      fue_mora INTEGER NOT NULL DEFAULT 0, tuvo_pago_parcial INTEGER NOT NULL DEFAULT 0,
      fue_recalculada INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE pagos (
      id INTEGER PRIMARY KEY AUTOINCREMENT, prestamo_id INTEGER NOT NULL, fecha_real TEXT NOT NULL, fecha_valor TEXT NOT NULL,
      fecha_registro TEXT NOT NULL, moneda_pago TEXT NOT NULL DEFAULT 'ARS', monto_moneda_pago TEXT NOT NULL,
      tc_aplicado TEXT, monto_moneda_contractual TEXT NOT NULL, monto_usd_ref TEXT, medio TEXT, referencia TEXT, nota TEXT,
      estado TEXT NOT NULL DEFAULT 'VALIDA', motivo_anulacion TEXT, creado_por TEXT,
      tipo_pago TEXT NOT NULL DEFAULT 'CUOTA', monto_a_capital TEXT NOT NULL DEFAULT '0', intereses_ahorrados TEXT NOT NULL DEFAULT '0',
      cuotas_restantes_antes INTEGER NOT NULL DEFAULT 0, cuotas_restantes_despues INTEGER NOT NULL DEFAULT 0,
      opcion_adelanto TEXT, interes_extra_generado TEXT NOT NULL DEFAULT '0',
      idempotency_key TEXT, idempotency_fingerprint TEXT, motor_version TEXT NOT NULL DEFAULT 'LEGACY', plan_hash TEXT, plan_json TEXT
    );
    CREATE UNIQUE INDEX ux_pagos_idempotency_key ON pagos(idempotency_key) WHERE idempotency_key IS NOT NULL;
    CREATE INDEX idx_pagos_motor_version ON pagos(motor_version);
    CREATE TABLE imputaciones (
      id INTEGER PRIMARY KEY AUTOINCREMENT, pago_id INTEGER NOT NULL, cuota_id INTEGER,
      concepto TEXT NOT NULL, monto TEXT NOT NULL, creado_en TEXT NOT NULL,
      origen TEXT NOT NULL DEFAULT 'SALDO_CONTRACTUAL', referencias_devengamiento TEXT NOT NULL DEFAULT '[]'
    );
    CREATE TABLE participaciones (
      id INTEGER PRIMARY KEY AUTOINCREMENT, prestamo_id INTEGER NOT NULL, inversor_id INTEGER NOT NULL,
      capital_aportado TEXT NOT NULL, moneda_aporte TEXT NOT NULL, tc_aporte TEXT, capital_usd_ref TEXT,
      porcentaje TEXT NOT NULL, fecha_aporte TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'ACTIVA', creado_en TEXT NOT NULL
    );
    CREATE TABLE ledger (
      id INTEGER PRIMARY KEY AUTOINCREMENT, entidad TEXT NOT NULL, entidad_id INTEGER NOT NULL,
      tipo_movimiento TEXT NOT NULL, debe TEXT NOT NULL, haber TEXT NOT NULL, fecha TEXT NOT NULL,
      metadata TEXT, correlacion_id TEXT NOT NULL, creado_en TEXT NOT NULL
    );
    CREATE TABLE auditoria (
      id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL, usuario TEXT NOT NULL,
      operacion TEXT NOT NULL, entidad TEXT NOT NULL, entidad_id INTEGER,
      datos_anteriores TEXT, datos_nuevos TEXT, motivo TEXT, correlacion_id TEXT NOT NULL
    );
    INSERT INTO personas(nombre, creado_en) VALUES ('Deudor', '2026-10-07');
    INSERT INTO prestamos(numero, deudor_id, capital_original, plazo_meses, sistema, convencion_dias, fecha_inicio, estado, creado_en)
      VALUES ('PR-000001', 1, '1000', 12, 'FRANCES', 'MENSUAL', '2026-10-01', 'ACTIVO', '2026-10-01');
    INSERT INTO versiones_tasa(prestamo_id, version, fecha_desde, tasa_anual, modalidad_tasa, creado_en)
      VALUES (1, 1, '2026-10-01', '0.24', 'TNA', '2026-10-01');
    INSERT INTO cuotas(version_id, numero, fecha_vencimiento, capital_inicial, interes, capital, cuota, saldo, creado_en)
      VALUES (1, 1, '2026-11-01', '1000', '20', '80', '100', '920', '2026-10-01');
    INSERT INTO cuotas(version_id, numero, fecha_vencimiento, capital_inicial, interes, capital, cuota, saldo, creado_en)
      VALUES (1, 2, '2026-12-01', '920', '18', '82', '100', '838', '2026-10-01');
    INSERT INTO participaciones(prestamo_id, inversor_id, capital_aportado, moneda_aporte, porcentaje, fecha_aporte, estado, creado_en)
      VALUES (1, 101, '500', 'ARS', '0.50', '2026-10-01', 'ACTIVA', '2026-10-01');
    INSERT INTO participaciones(prestamo_id, inversor_id, capital_aportado, moneda_aporte, porcentaje, fecha_aporte, estado, creado_en)
      VALUES (1, 202, '500', 'ARS', '0.50', '2026-10-01', 'ACTIVA', '2026-10-01');
    ''')
    db.conn.commit()
    aplicar(db)
    db.conn.commit()


def cmd(**changes):
    data = {
        'prestamo_id': 1, 'monto': Decimal('100'),
        'fecha_real': date(2026, 11, 1), 'usuario': 'admin',
        'idempotency_key': 'complete-1',
    }
    data.update(changes)
    return RegistrarPagoCommand(**data)


def factory(db):
    return crear_registrador_pago_v3_completo(
        db,
        tasa_anual=Decimal('0.24'),
        modalidad_tasa=ModalidadTasa.TNA,
        convencion_dias=ConvencionDias.ACTUAL_365,
    )


def test_distribucion_inversores_atomica_y_misma_correlacion(tmp_path):
    db = DB(tmp_path / 'a.db'); setup(db)
    try:
        r = factory(db).ejecutar(cmd())
        rows = db.consultar('SELECT entidad_id AS inversor_id, tipo_movimiento, debe, haber, correlacion_id FROM ledger WHERE tipo_movimiento IN (\'COBRO_PAGO\',\'DISTRIBUCION_INVERSOR\') ORDER BY id')
        assert [(x['inversor_id'], x['tipo_movimiento'], Decimal(x['debe']), Decimal(x['haber'])) for x in rows] == [
            (101, 'COBRO_PAGO', Decimal('50'), Decimal('0')),
            (1, 'DISTRIBUCION_INVERSOR', Decimal('0'), Decimal('50')),
            (202, 'COBRO_PAGO', Decimal('50'), Decimal('0')),
            (1, 'DISTRIBUCION_INVERSOR', Decimal('0'), Decimal('50')),
        ]
        core = db.consultar_uno("SELECT correlacion_id FROM ledger WHERE entidad='PAGO' AND entidad_id=?", (r.pago_id,))['correlacion_id']
        assert all(x['correlacion_id'] == core for x in rows)
        assert db.consultar_uno("SELECT COUNT(*) n FROM auditoria WHERE operacion='PAGO_DISTRIBUCION_INVERSORES'")['n'] == 1
        assert db.consultar_uno('SELECT revision_prestamo FROM prestamos WHERE id=1')['revision_prestamo'] == 1
    finally:
        db.close()


def test_idempotencia_no_duplica_distribucion(tmp_path):
    db = DB(tmp_path / 'b.db'); setup(db)
    try:
        caso = factory(db)
        a = caso.ejecutar(cmd())
        b = caso.ejecutar(cmd())
        assert a.pago_id == b.pago_id
        assert b.es_repeticion_idempotente
        assert db.consultar_uno("SELECT COUNT(*) n FROM ledger WHERE tipo_movimiento='COBRO_PAGO'")['n'] == 2
        assert db.consultar_uno("SELECT COUNT(*) n FROM auditoria WHERE operacion='PAGO_DISTRIBUCION_INVERSORES'")['n'] == 1
    finally:
        db.close()


def test_porcentajes_invalidos_revierten_pago_evento_y_revision(tmp_path):
    db = DB(tmp_path / 'c.db'); setup(db)
    try:
        db.ejecutar("UPDATE participaciones SET porcentaje='0.60' WHERE inversor_id=202")
        db.conn.commit()
        with pytest.raises(ErrorInvariante, match='100%'):
            factory(db).ejecutar(cmd(idempotency_key='bad'))
        assert db.consultar_uno('SELECT COUNT(*) n FROM pagos')['n'] == 0
        assert db.consultar_uno('SELECT COUNT(*) n FROM devengamientos')['n'] == 0
        assert db.consultar_uno('SELECT COUNT(*) n FROM ledger')['n'] == 0
        assert db.consultar_uno('SELECT COUNT(*) n FROM auditoria')['n'] == 0
        assert db.consultar_uno('SELECT revision_prestamo FROM prestamos WHERE id=1')['revision_prestamo'] == 0
    finally:
        db.close()


def test_sin_participaciones_no_crea_distribucion(tmp_path):
    db = DB(tmp_path / 'd.db'); setup(db)
    try:
        db.ejecutar("UPDATE participaciones SET estado='INACTIVA'")
        db.conn.commit()
        factory(db).ejecutar(cmd(idempotency_key='none'))
        assert db.consultar_uno("SELECT COUNT(*) n FROM ledger WHERE tipo_movimiento='COBRO_PAGO'")['n'] == 0
        assert db.consultar_uno("SELECT COUNT(*) n FROM auditoria WHERE operacion='PAGO_DISTRIBUCION_INVERSORES'")['n'] == 0
        assert db.consultar_uno('SELECT COUNT(*) n FROM pagos')['n'] == 1
    finally:
        db.close()


def test_fallo_distribucion_revierten_toda_la_operacion(tmp_path):
    db = DB(tmp_path / 'e.db'); setup(db)
    try:
        db.ejecutar("UPDATE participaciones SET porcentaje='0.9999' WHERE inversor_id=101")
        db.ejecutar("UPDATE participaciones SET porcentaje='0.0000' WHERE inversor_id=202")
        db.conn.commit()
        with pytest.raises(ErrorInvariante):
            factory(db).ejecutar(cmd(idempotency_key='bad2'))
        assert db.consultar_uno('SELECT COUNT(*) n FROM pagos')['n'] == 0
        assert db.consultar_uno('SELECT COUNT(*) n FROM devengamientos')['n'] == 0
        assert db.consultar_uno('SELECT COUNT(*) n FROM ledger')['n'] == 0
        assert db.consultar_uno('SELECT revision_prestamo FROM prestamos WHERE id=1')['revision_prestamo'] == 0
    finally:
        db.close()


def test_campo_legacy_interes_extra_generado_refleja_devengamiento(tmp_path):
    db = DB(tmp_path / 'compat.db'); setup(db)
    try:
        r = factory(db).ejecutar(cmd(idempotency_key='compat-interest', fecha_real=date(2026,11,11), fecha_valor=date(2026,11,11)))
        fila = db.consultar_uno('SELECT interes_extra_generado FROM pagos WHERE id=?', (r.pago_id,))
        assert Decimal(fila['interes_extra_generado']) == Decimal('0.53')
    finally:
        db.close()
