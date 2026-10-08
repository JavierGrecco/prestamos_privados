from datetime import date
from decimal import Decimal
import sqlite3

from infraestructura.repositorios.registro_pago_v3 import RepositorioRegistroPagoSQLiteV3


class DB:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
    @property
    def conexion(self): return self.conn
    def ejecutar(self, sql, params=()): return self.conn.execute(sql, params)
    def consultar(self, sql, params=()): return self.conn.execute(sql, params).fetchall()
    def consultar_uno(self, sql, params=()): return self.conn.execute(sql, params).fetchone()
    def close(self): self.conn.close()


def setup(db):
    db.conn.executescript('''
    CREATE TABLE prestamos(id INTEGER PRIMARY KEY, estado TEXT, revision_prestamo INTEGER);
    CREATE TABLE versiones_tasa(id INTEGER PRIMARY KEY, prestamo_id INTEGER, fecha_hasta TEXT, version INTEGER);
    CREATE TABLE cuotas(
      id INTEGER PRIMARY KEY, version_id INTEGER, numero INTEGER, fecha_vencimiento TEXT,
      estado TEXT, interes TEXT, capital TEXT, cuota TEXT, interes_pendiente TEXT, capital_pendiente TEXT,
      mora_pendiente TEXT, monto_pendiente TEXT, tuvo_pago_parcial INTEGER
    );
    INSERT INTO prestamos VALUES (1,'ACTIVO',0);
    INSERT INTO versiones_tasa VALUES (1,1,NULL,1);
    INSERT INTO cuotas VALUES (1,1,1,'2026-11-01','PENDIENTE','20','80','100','0','0','0','0',0);
    INSERT INTO cuotas VALUES (2,1,2,'2026-12-01','PENDIENTE','18','82','100','0','0','0','0',0);
    INSERT INTO cuotas VALUES (3,1,3,'2027-01-01','PENDIENTE','16','84','100','0','0','0','0',0);
    ''')
    db.conn.commit()


def test_snapshot_solo_llega_hasta_primera_pendiente(tmp_path):
    db = DB(tmp_path/'a.db'); setup(db)
    try:
        estado = RepositorioRegistroPagoSQLiteV3(db).obtener_estado_pago(1)
        assert [o.numero_cuota for o in estado.obligaciones] == [1]
        assert estado.obligaciones[0].saldo.interes == Decimal('20.00')
        assert estado.obligaciones[0].saldo.capital == Decimal('80.00')
    finally: db.close()


def test_snapshot_incluye_arrastre_parcial_y_primera_pendiente(tmp_path):
    db = DB(tmp_path/'b.db'); setup(db)
    try:
        db.ejecutar("UPDATE cuotas SET estado='PARCIAL', interes_pendiente='5', capital_pendiente='30', monto_pendiente='35', tuvo_pago_parcial=1 WHERE id=1")
        db.conn.commit()
        estado = RepositorioRegistroPagoSQLiteV3(db).obtener_estado_pago(1)
        assert [o.numero_cuota for o in estado.obligaciones] == [1,2]
        assert estado.obligaciones[0].saldo.total == Decimal('35.00')
    finally: db.close()


def test_cuotas_reestructuradas_quedan_fuera_del_horizonte(tmp_path):
    db = DB(tmp_path/'c.db'); setup(db)
    try:
        db.ejecutar("UPDATE cuotas SET estado='REESTRUCTURADA', monto_pendiente='0', interes_pendiente='0', capital_pendiente='0', mora_pendiente='0' WHERE id=1")
        db.conn.commit()
        estado = RepositorioRegistroPagoSQLiteV3(db).obtener_estado_pago(1)
        assert [o.numero_cuota for o in estado.obligaciones] == [2]
    finally: db.close()
