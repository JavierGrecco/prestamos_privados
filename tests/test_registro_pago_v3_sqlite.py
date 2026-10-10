from datetime import date
from decimal import Decimal
import sqlite3
from contextlib import contextmanager
from threading import RLock

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.registro_pago_v3 import RegistrarPagoV3
from dominio.excepciones import ErrorInvariante, ErrorValidacion
from dominio.motor_pagos_v3 import calcular_plan_pago
from infraestructura.repositorios.registro_pago_v3 import RepositorioRegistroPagoSQLiteV3


class DB:
    def __init__(self, path):
        self._lock = RLock()
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")

    @contextmanager
    def bloqueo_transaccion_explicita(self):
        with self._lock:
            yield self

    @property
    def conexion(self):
        with self._lock:
            return self.conn

    def ejecutar(self, sql, params=()):
        with self._lock:
            return self.conn.execute(sql, params)

    def consultar(self, sql, params=()):
        with self._lock:
            return self.conn.execute(sql, params).fetchall()

    def consultar_uno(self, sql, params=()):
        with self._lock:
            return self.conn.execute(sql, params).fetchone()

    def ultimo_id_insertado(self):
        with self._lock:
            return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def close(self):
        with self._lock:
            self.conn.close()

def setup(db):
    db.conn.executescript("""
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
    """)
    db.conn.commit()


def command(**changes):
    data = {'prestamo_id': 1, 'monto': Decimal('100.00'), 'fecha_real': date(2026, 11, 1), 'usuario': 'admin'}
    data.update(changes)
    return RegistrarPagoCommand(**data)


def calc(**kwargs):
    return calcular_plan_pago(**kwargs)


def test_persistencia_exacta_y_multicapa(tmp_path):
    db = DB(tmp_path/'a.db'); setup(db)
    try:
        r = RepositorioRegistroPagoSQLiteV3(db)
        result = RegistrarPagoV3(r, calc).ejecutar(command(idempotency_key='p-1'))
        assert result.pago_id == 1
        assert db.consultar_uno('SELECT estado, monto_pendiente FROM cuotas WHERE id=1')['estado'] == 'PAGADA'
        assert Decimal(db.consultar_uno('SELECT monto_pendiente FROM cuotas WHERE id=1')['monto_pendiente']) == 0
        rows = db.consultar('SELECT cuota_id, concepto, monto, origen FROM imputaciones WHERE pago_id=1 ORDER BY id')
        assert [(x['cuota_id'], x['concepto'], Decimal(x['monto']), x['origen']) for x in rows] == [
            (1,'INTERES',Decimal('20'),'SALDO_CONTRACTUAL'), (1,'CAPITAL',Decimal('80'),'SALDO_CONTRACTUAL')]
        led = db.consultar_uno("SELECT SUM(CAST(debe AS REAL)) d, SUM(CAST(haber AS REAL)) h FROM ledger")
        assert Decimal(str(led['d'])) == Decimal('100.0') and Decimal(str(led['h'])) == Decimal('100.0')
        assert db.consultar_uno("SELECT operacion FROM auditoria WHERE operacion='PAGO_REGISTRADO_V3'") is not None
        p = db.consultar_uno('SELECT motor_version, plan_hash, plan_json FROM pagos WHERE id=1')
        assert p['motor_version'] == 'V3-F3.1' and len(p['plan_hash']) == 64 and p['plan_json']
        assert db.consultar_uno('SELECT revision_prestamo FROM prestamos WHERE id=1')['revision_prestamo'] == 1
    finally: db.close()


def test_idempotencia_no_duplica_pago_ni_revision(tmp_path):
    db = DB(tmp_path/'b.db'); setup(db)
    try:
        r = RepositorioRegistroPagoSQLiteV3(db); c = command(idempotency_key='idem')
        a = RegistrarPagoV3(r, calc).ejecutar(c); b = RegistrarPagoV3(r, calc).ejecutar(c)
        assert a.pago_id == b.pago_id == 1 and b.es_repeticion_idempotente
        assert db.consultar_uno('SELECT COUNT(*) n FROM pagos')['n'] == 1
        assert db.consultar_uno('SELECT revision_prestamo FROM prestamos WHERE id=1')['revision_prestamo'] == 1
    finally: db.close()


def test_idempotencia_misma_clave_payload_diferente_es_error(tmp_path):
    db = DB(tmp_path/'c.db'); setup(db)
    try:
        r = RepositorioRegistroPagoSQLiteV3(db); RegistrarPagoV3(r, calc).ejecutar(command(idempotency_key='idem'))
        with pytest.raises(ErrorInvariante, match='payload diferente'):
            RegistrarPagoV3(r, calc).ejecutar(command(idempotency_key='idem', monto=Decimal('90')))
        assert db.consultar_uno('SELECT COUNT(*) n FROM pagos')['n'] == 1
    finally: db.close()


def test_revision_obsoleta_no_persiste(tmp_path):
    db = DB(tmp_path/'d.db'); setup(db)
    try:
        with pytest.raises(ErrorInvariante, match='Conflicto de revisión'):
            RegistrarPagoV3(RepositorioRegistroPagoSQLiteV3(db), calc).ejecutar(command(revision_prestamo=4))
        assert db.consultar_uno('SELECT COUNT(*) n FROM pagos')['n'] == 0
    finally: db.close()


def test_excedente_no_se_persiste_sin_rai_rni(tmp_path):
    db = DB(tmp_path/'e.db'); setup(db)
    try:
        with pytest.raises(ErrorValidacion, match='excedente'):
            RegistrarPagoV3(RepositorioRegistroPagoSQLiteV3(db), calc).ejecutar(command(monto=Decimal('250')))
        assert db.consultar_uno('SELECT COUNT(*) n FROM pagos')['n'] == 0
    finally: db.close()


def test_rollback_total_ante_fallo_de_ledger(tmp_path):
    db = DB(tmp_path/'f.db'); setup(db)
    try:
        db.conn.execute("CREATE TRIGGER romper BEFORE INSERT ON ledger BEGIN SELECT RAISE(ABORT,'fallo controlado'); END;")
        with pytest.raises(Exception, match='fallo controlado'):
            RegistrarPagoV3(RepositorioRegistroPagoSQLiteV3(db), calc).ejecutar(command(idempotency_key='rollback'))
        assert db.consultar_uno('SELECT COUNT(*) n FROM pagos')['n'] == 0
        assert db.consultar_uno('SELECT COUNT(*) n FROM imputaciones')['n'] == 0
        assert db.consultar_uno('SELECT COUNT(*) n FROM auditoria')['n'] == 0
        assert db.consultar_uno('SELECT revision_prestamo FROM prestamos WHERE id=1')['revision_prestamo'] == 0
        assert db.consultar_uno('SELECT estado FROM cuotas WHERE id=1')['estado'] == 'PENDIENTE'
    finally: db.close()


def test_begin_es_inmediato_y_bloquea_otro_escritor(tmp_path):
    path = tmp_path / 'lock.db'
    db1 = DB(path); setup(db1)
    db2 = DB(path)
    db2.conn.execute('PRAGMA busy_timeout=0')
    try:
        r1 = RepositorioRegistroPagoSQLiteV3(db1)
        r2 = RepositorioRegistroPagoSQLiteV3(db2)
        r1.begin()
        try:
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                r2.begin()
        finally:
            r1.rollback()
    finally:
        db2.close(); db1.close()


def test_factory_construye_el_caso_de_uso_v3(tmp_path):
    from aplicacion.servicios.fabrica_registro_pago_v3 import crear_registrador_pago_v3
    db = DB(tmp_path/'factory.db'); setup(db)
    try:
        caso = crear_registrador_pago_v3(db, calc)
        assert isinstance(caso, __import__('aplicacion.servicios.registro_pago_v3', fromlist=['RegistrarPagoV3']).RegistrarPagoV3)
        resultado = caso.ejecutar(command())
        assert resultado.pago_id == 1
    finally: db.close()
