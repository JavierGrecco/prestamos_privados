from decimal import Decimal
import json
import sqlite3

import pytest

from infraestructura.consultas.pagos_v3 import obtener_pago_v3
from dominio.excepciones import ErrorInvariante, ErrorValidacion


class DB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

    def executescript(self, sql):
        return self.conn.executescript(sql)

    def ejecutar(self, sql, params=()):
        return self.conn.execute(sql, params)

    def consultar(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def consultar_uno(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()


def setup_db():
    db = DB()
    db.executescript("""
    CREATE TABLE pagos (
      id INTEGER PRIMARY KEY, prestamo_id INTEGER, fecha_real TEXT, fecha_valor TEXT,
      monto_moneda_contractual TEXT, moneda_pago TEXT, tipo_pago TEXT,
      monto_a_capital TEXT, intereses_ahorrados TEXT,
      cuotas_restantes_antes INTEGER, cuotas_restantes_despues INTEGER,
      opcion_adelanto TEXT, motor_version TEXT, plan_hash TEXT, plan_json TEXT
    );
    CREATE TABLE imputaciones (
      id INTEGER PRIMARY KEY, pago_id INTEGER, cuota_id INTEGER, concepto TEXT,
      monto TEXT, origen TEXT, referencias_devengamiento TEXT
    );
    CREATE TABLE ledger (
      id INTEGER PRIMARY KEY, entidad TEXT, entidad_id INTEGER, tipo_movimiento TEXT,
      debe TEXT, haber TEXT, fecha TEXT, correlacion_id TEXT, metadata TEXT
    );
    CREATE TABLE auditoria (
      id INTEGER PRIMARY KEY, fecha TEXT, usuario TEXT, operacion TEXT,
      entidad TEXT, entidad_id INTEGER, motivo TEXT, correlacion_id TEXT
    );
    """)
    plan_json = json.dumps({"tipo":"CUOTA"}, separators=(",",":"))
    import hashlib
    plan_hash = hashlib.sha256(plan_json.encode("utf-8")).hexdigest()
    db.ejecutar("""INSERT INTO pagos VALUES (1,1,'2026-10-07','2026-10-07','100.00','ARS','CUOTA','80.00','0.00',4,3,NULL,'V3-G4',?,?)""", (plan_hash, plan_json))
    db.ejecutar("INSERT INTO imputaciones VALUES (1,1,10,'INTERES','20.00','SALDO_CONTRACTUAL','[]')")
    db.ejecutar("INSERT INTO imputaciones VALUES (2,1,10,'CAPITAL','80.00','SALDO_CONTRACTUAL','[]')")
    db.ejecutar("INSERT INTO ledger VALUES (1,'PRESTAMO',1,'PAGO_RECIBIDO','0','100.00','2026-10-07','corr-1',?)", ('{"pago_id":1}',))
    db.ejecutar("INSERT INTO ledger VALUES (2,'PAGO',1,'PAGO','100.00','0','2026-10-07','corr-1',?)", ('{"prestamo_id":1}',))
    db.ejecutar("INSERT INTO ledger VALUES (3,'INVERSOR',101,'COBRO_PAGO','50.00','0','2026-10-07','corr-1',?)", ('{"pago_id":1}',))
    db.ejecutar("INSERT INTO ledger VALUES (4,'PRESTAMO',1,'DISTRIBUCION_INVERSOR','0','50.00','2026-10-07','corr-1',?)", ('{"pago_id":1}',))
    db.ejecutar("INSERT INTO ledger VALUES (5,'INVERSOR',202,'COBRO_PAGO','50.00','0','2026-10-07','corr-1',?)", ('{"pago_id":1}',))
    db.ejecutar("INSERT INTO ledger VALUES (6,'PRESTAMO',1,'DISTRIBUCION_INVERSOR','0','50.00','2026-10-07','corr-1',?)", ('{"pago_id":1}',))
    db.ejecutar("INSERT INTO auditoria VALUES (1,'2026-10-07','admin','PAGO_REGISTRADO_V3','PAGO',1,'Registro V3','corr-1')")
    db.conn.commit()
    return db


def test_read_model_reconcilia_cadena_completa():
    db=setup_db()
    r=obtener_pago_v3(db,1)
    assert r.monto==Decimal('100.00')
    assert len(r.imputaciones)==2
    assert r.reconciliacion.integra
    assert r.reconciliacion.dinero_conservado
    assert r.reconciliacion.ledger_pago_balanceado
    assert r.reconciliacion.suma_distribucion_inversores==Decimal('100.00')
    assert r.plan=={'tipo':'CUOTA'}


def test_read_model_no_muta_base():
    db=setup_db()
    before={t:db.ejecutar(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ('pagos','imputaciones','ledger','auditoria')}
    obtener_pago_v3(db,1)
    after={t:db.ejecutar(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in before}
    assert after==before


def test_read_model_detecta_imputaciones_incompletas():
    db=setup_db()
    db.ejecutar("UPDATE imputaciones SET monto='90.00' WHERE id=2")
    with pytest.raises(ErrorInvariante, match='inconsistencia'):
        obtener_pago_v3(db,1)


def test_read_model_acepta_pago_sin_distribucion():
    db=setup_db()
    db.ejecutar("DELETE FROM ledger WHERE tipo_movimiento IN ('DISTRIBUCION_INVERSOR','COBRO_PAGO')")
    db.conn.commit()
    r=obtener_pago_v3(db,1)
    assert not r.reconciliacion.hay_distribucion_inversores
    assert r.reconciliacion.integra


def test_read_model_detecta_json_invalido():
    db=setup_db()
    db.ejecutar("UPDATE imputaciones SET referencias_devengamiento='{' WHERE id=1")
    with pytest.raises(ErrorInvariante, match='JSON inválido'):
        obtener_pago_v3(db,1)


def test_read_model_pago_inexistente():
    db=setup_db()
    with pytest.raises(ErrorValidacion, match='no existe'):
        obtener_pago_v3(db,99)


def test_read_model_detecta_plan_hash_corrupto():
    db=setup_db()
    db.ejecutar("UPDATE pagos SET plan_hash='0000' WHERE id=1")
    with pytest.raises(ErrorInvariante, match='plan_hash'):
        obtener_pago_v3(db,1)


def test_read_model_detecta_correlacion_contable_inconsistente():
    db=setup_db()
    db.ejecutar("UPDATE ledger SET correlacion_id='otra' WHERE id=3")
    with pytest.raises(ErrorInvariante, match='correlaciones distintas'):
        obtener_pago_v3(db,1)


def test_read_model_detecta_correlacion_auditoria_inconsistente():
    db=setup_db()
    db.ejecutar("UPDATE auditoria SET correlacion_id='otra' WHERE id=1")
    with pytest.raises(ErrorInvariante, match='correlación del ledger'):
        obtener_pago_v3(db,1)
