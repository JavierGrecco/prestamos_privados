from datetime import date
from decimal import Decimal
import sqlite3
from contextlib import contextmanager
from threading import RLock

import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.fabrica_registro_pago_v3 import crear_registrador_pago_v3_completo_con_adelantos
from dominio.excepciones import ErrorInvariante, ErrorValidacion
from dominio.tipos import ConvencionDias, ModalidadTasa
from infraestructura.migraciones.v010_devengamientos_v3 import aplicar


class DB:
    def __init__(self, path):
        self._lock = RLock()
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

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
            return self.conn.execute('SELECT last_insert_rowid()').fetchone()[0]

    def close(self):
        with self._lock:
            self.conn.close()

def setup(db):
    db.conn.executescript('''
    CREATE TABLE personas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, creado_en TEXT NOT NULL);
    CREATE TABLE prestamos (id INTEGER PRIMARY KEY AUTOINCREMENT, numero TEXT UNIQUE NOT NULL, deudor_id INTEGER NOT NULL,
      moneda_contractual TEXT NOT NULL DEFAULT 'ARS', capital_original TEXT NOT NULL, plazo_meses INTEGER NOT NULL,
      sistema TEXT NOT NULL, convencion_dias TEXT NOT NULL, tc_inicial TEXT, fecha_inicio TEXT NOT NULL, fecha_fin_estimada TEXT,
      estado TEXT NOT NULL DEFAULT 'ACTIVO', destino TEXT, descripcion TEXT, creado_en TEXT NOT NULL, actualizado_en TEXT,
      revision_prestamo INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE versiones_tasa (id INTEGER PRIMARY KEY AUTOINCREMENT, prestamo_id INTEGER NOT NULL, version INTEGER NOT NULL,
      fecha_desde TEXT NOT NULL, fecha_hasta TEXT, tasa_anual TEXT NOT NULL, modalidad_tasa TEXT NOT NULL,
      motivo TEXT, creado_por TEXT, creado_en TEXT NOT NULL);
    CREATE TABLE cuotas (id INTEGER PRIMARY KEY AUTOINCREMENT, version_id INTEGER NOT NULL, numero INTEGER NOT NULL,
      fecha_vencimiento TEXT NOT NULL, capital_inicial TEXT NOT NULL, interes TEXT NOT NULL, capital TEXT NOT NULL,
      cuota TEXT NOT NULL, saldo TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'PENDIENTE', creado_en TEXT NOT NULL,
      monto_pendiente TEXT NOT NULL DEFAULT '0', interes_pendiente TEXT NOT NULL DEFAULT '0', capital_pendiente TEXT NOT NULL DEFAULT '0',
      mora_pendiente TEXT NOT NULL DEFAULT '0', fue_mora INTEGER NOT NULL DEFAULT 0, tuvo_pago_parcial INTEGER NOT NULL DEFAULT 0,
      fue_recalculada INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE pagos (id INTEGER PRIMARY KEY AUTOINCREMENT, prestamo_id INTEGER NOT NULL, fecha_real TEXT NOT NULL, fecha_valor TEXT NOT NULL,
      fecha_registro TEXT NOT NULL, moneda_pago TEXT NOT NULL DEFAULT 'ARS', monto_moneda_pago TEXT NOT NULL, tc_aplicado TEXT,
      monto_moneda_contractual TEXT NOT NULL, monto_usd_ref TEXT, medio TEXT, referencia TEXT, nota TEXT, estado TEXT NOT NULL DEFAULT 'VALIDA',
      motivo_anulacion TEXT, creado_por TEXT, tipo_pago TEXT NOT NULL DEFAULT 'CUOTA', monto_a_capital TEXT NOT NULL DEFAULT '0',
      intereses_ahorrados TEXT NOT NULL DEFAULT '0', cuotas_restantes_antes INTEGER NOT NULL DEFAULT 0, cuotas_restantes_despues INTEGER NOT NULL DEFAULT 0,
      opcion_adelanto TEXT, interes_extra_generado TEXT NOT NULL DEFAULT '0', idempotency_key TEXT, idempotency_fingerprint TEXT,
      motor_version TEXT NOT NULL DEFAULT 'LEGACY', plan_hash TEXT, plan_json TEXT);
    CREATE UNIQUE INDEX ux_pagos_idempotency_key ON pagos(idempotency_key) WHERE idempotency_key IS NOT NULL;
    CREATE INDEX idx_pagos_motor_version ON pagos(motor_version);
    CREATE TABLE imputaciones (id INTEGER PRIMARY KEY AUTOINCREMENT, pago_id INTEGER NOT NULL, cuota_id INTEGER, concepto TEXT NOT NULL,
      monto TEXT NOT NULL, creado_en TEXT NOT NULL, origen TEXT NOT NULL DEFAULT 'SALDO_CONTRACTUAL', referencias_devengamiento TEXT NOT NULL DEFAULT '[]');
    CREATE TABLE participaciones (id INTEGER PRIMARY KEY AUTOINCREMENT, prestamo_id INTEGER NOT NULL, inversor_id INTEGER NOT NULL,
      capital_aportado TEXT NOT NULL, moneda_aporte TEXT NOT NULL, tc_aporte TEXT, capital_usd_ref TEXT, porcentaje TEXT NOT NULL,
      fecha_aporte TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'ACTIVA', creado_en TEXT NOT NULL);
    CREATE TABLE ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, entidad TEXT NOT NULL, entidad_id INTEGER NOT NULL, tipo_movimiento TEXT NOT NULL,
      debe TEXT NOT NULL, haber TEXT NOT NULL, fecha TEXT NOT NULL, metadata TEXT, correlacion_id TEXT NOT NULL, creado_en TEXT NOT NULL);
    CREATE TABLE auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL, usuario TEXT NOT NULL, operacion TEXT NOT NULL,
      entidad TEXT NOT NULL, entidad_id INTEGER, datos_anteriores TEXT, datos_nuevos TEXT, motivo TEXT, correlacion_id TEXT NOT NULL);
    CREATE TABLE historial_recalculos (id INTEGER PRIMARY KEY AUTOINCREMENT, prestamo_id INTEGER NOT NULL, pago_id INTEGER NOT NULL,
      tipo TEXT NOT NULL, fecha TEXT NOT NULL, capital_antes TEXT NOT NULL, capital_despues TEXT NOT NULL,
      cuotas_antes INTEGER NOT NULL, cuotas_despues INTEGER NOT NULL, intereses_antes TEXT NOT NULL, intereses_despues TEXT NOT NULL,
      detalle_json TEXT, creado_en TEXT NOT NULL, cuota_objetivo_numero INTEGER NOT NULL DEFAULT 0);
    INSERT INTO personas(nombre, creado_en) VALUES ('Deudor','2026-10-07');
    INSERT INTO prestamos(numero,deudor_id,capital_original,plazo_meses,sistema,convencion_dias,fecha_inicio,estado,creado_en)
      VALUES ('PR-1',1,'1000',4,'frances','actual_365','2026-10-01','ACTIVO','2026-10-01');
    INSERT INTO versiones_tasa(prestamo_id,version,fecha_desde,tasa_anual,modalidad_tasa,creado_en)
      VALUES (1,1,'2026-10-01','0.24','TNA','2026-10-01');
    INSERT INTO cuotas(version_id,numero,fecha_vencimiento,capital_inicial,interes,capital,cuota,saldo,creado_en)
      VALUES (1,1,'2026-11-01','1000','20','80','100','920','2026-10-01');
    INSERT INTO cuotas(version_id,numero,fecha_vencimiento,capital_inicial,interes,capital,cuota,saldo,creado_en)
      VALUES (1,2,'2026-12-01','920','18','82','100','838','2026-10-01');
    INSERT INTO cuotas(version_id,numero,fecha_vencimiento,capital_inicial,interes,capital,cuota,saldo,creado_en)
      VALUES (1,3,'2027-01-01','838','16','84','100','754','2026-10-01');
    INSERT INTO cuotas(version_id,numero,fecha_vencimiento,capital_inicial,interes,capital,cuota,saldo,creado_en)
      VALUES (1,4,'2027-02-01','754','14','86','100','668','2026-10-01');
    INSERT INTO participaciones(prestamo_id,inversor_id,capital_aportado,moneda_aporte,porcentaje,fecha_aporte,estado,creado_en)
      VALUES (1,101,'500','ARS','0.50','2026-10-01','ACTIVA','2026-10-01');
    INSERT INTO participaciones(prestamo_id,inversor_id,capital_aportado,moneda_aporte,porcentaje,fecha_aporte,estado,creado_en)
      VALUES (1,202,'500','ARS','0.50','2026-10-01','ACTIVA','2026-10-01');
    ''')
    db.conn.commit(); aplicar(db); db.conn.commit()


def rai_stub(**kwargs):
    return [
      {'capital_inicial':'870','interes':'10','capital':'280','cuota':'290','saldo':'590','vencimiento':date(1900,1,1)},
      {'capital_inicial':'590','interes':'7','capital':'290','cuota':'297','saldo':'300','vencimiento':date(1900,2,1)},
      {'capital_inicial':'300','interes':'4','capital':'300','cuota':'304','saldo':'0','vencimiento':date(1900,3,1)},
    ]


def rni_stub(**kwargs):
    return ([
      {'capital_inicial':'870','interes':'10','capital':'400','cuota':'410','saldo':'470','vencimiento':date(1900,1,1)},
      {'capital_inicial':'470','interes':'7','capital':'470','cuota':'477','saldo':'0','vencimiento':date(1900,2,1)},
    ], 2)


def factory(db, rai=rai_stub, rni=rni_stub):
    return crear_registrador_pago_v3_completo_con_adelantos(
      db, tasa_anual=Decimal('0.24'), modalidad_tasa=ModalidadTasa.TNA,
      convencion_dias=ConvencionDias.ACTUAL_365, recalcular_rai_fn=rai, recalcular_rni_fn=rni,
    )


def cmd(**changes):
    data={'prestamo_id':1,'monto':Decimal('150'),'fecha_real':date(2026,11,1),'usuario':'admin','idempotency_key':'adv-1','opcion_adelanto':'RAI'}
    data.update(changes); return RegistrarPagoCommand(**data)


def test_rai_reemplaza_futuro_sin_borrar_historia(tmp_path):
    db=DB(tmp_path/'a.db'); setup(db)
    try:
      r=factory(db).ejecutar(cmd())
      assert r.pago_id==1
      old=db.consultar("SELECT id,estado,numero FROM cuotas WHERE id IN (2,3,4) ORDER BY id")
      assert [(x['id'],x['estado']) for x in old]==[(2,'REESTRUCTURADA'),(3,'REESTRUCTURADA'),(4,'REESTRUCTURADA')]
      new=db.consultar("SELECT id,numero,estado,capital_pendiente,interes_pendiente FROM cuotas WHERE id>4 ORDER BY id")
      assert len(new)==3 and [x['numero'] for x in new]==[2,3,4]
      pago=db.consultar_uno('SELECT tipo_pago,monto_a_capital,intereses_ahorrados,cuotas_restantes_despues,opcion_adelanto FROM pagos WHERE id=1')
      assert pago['tipo_pago']=='ADELANTO_RAI'
      assert Decimal(pago['monto_a_capital'])==Decimal('130.00')
      assert Decimal(pago['intereses_ahorrados'])==Decimal('27.00')
      assert pago['cuotas_restantes_despues']==3
      assert pago['opcion_adelanto']=='RAI'
      apps=db.consultar('SELECT cuota_id,concepto,monto,origen FROM imputaciones WHERE pago_id=1 ORDER BY id')
      assert [(x['cuota_id'],x['concepto'],Decimal(x['monto']),x['origen']) for x in apps]==[
        (1,'INTERES',Decimal('20'),'SALDO_CONTRACTUAL'),(1,'CAPITAL',Decimal('80'),'SALDO_CONTRACTUAL'),(None,'CAPITAL',Decimal('50'),'PREPAGO')]
      hist=db.consultar_uno('SELECT tipo,capital_antes,capital_despues,cuotas_antes,cuotas_despues,cuota_objetivo_numero FROM historial_recalculos WHERE pago_id=1')
      assert hist['tipo']=='RAI' and Decimal(hist['capital_antes'])==Decimal('920') and Decimal(hist['capital_despues'])==Decimal('870')
      assert hist['cuotas_antes']==3 and hist['cuotas_despues']==3 and hist['cuota_objetivo_numero']==1
    finally: db.close()


def test_idempotencia_no_duplica_reestructuracion(tmp_path):
    db=DB(tmp_path/'b.db'); setup(db)
    try:
      caso=factory(db); a=caso.ejecutar(cmd()); b=caso.ejecutar(cmd())
      assert b.es_repeticion_idempotente and a.pago_id==b.pago_id
      assert db.consultar_uno('SELECT COUNT(*) n FROM pagos')['n']==1
      assert db.consultar_uno('SELECT COUNT(*) n FROM historial_recalculos')['n']==1
      assert db.consultar_uno("SELECT COUNT(*) n FROM cuotas WHERE estado='REESTRUCTURADA'")['n']==3
    finally: db.close()


def test_rni_acorta_plazo_en_fechas_existentes(tmp_path):
    db=DB(tmp_path/'c.db'); setup(db)
    try:
      r=factory(db).ejecutar(cmd(opcion_adelanto='RNI',idempotency_key='rni'))
      assert r.pago_id==1
      new=db.consultar("SELECT numero,fecha_vencimiento FROM cuotas WHERE estado='PENDIENTE' ORDER BY numero")
      assert [(x['numero'],x['fecha_vencimiento']) for x in new]==[(2,'2026-12-01'),(3,'2027-01-01')]
      assert db.consultar_uno('SELECT cuotas_despues FROM historial_recalculos WHERE pago_id=1')['cuotas_despues']==2
      ahorro = Decimal(db.consultar_uno('SELECT intereses_ahorrados FROM pagos WHERE id=1')['intereses_ahorrados'])
      assert ahorro == Decimal('31.00')

      correlacion = db.consultar_uno(
        "SELECT correlacion_id FROM ledger WHERE entidad='PAGO' AND entidad_id=1 LIMIT 1"
      )["correlacion_id"]
      cobrado = db.consultar_uno(
        "SELECT COALESCE(SUM(CAST(debe AS REAL)), 0) AS total "
        "FROM ledger WHERE tipo_movimiento='COBRO_PAGO' AND correlacion_id=?",
        (correlacion,),
      )
      distribuido = db.consultar_uno(
        "SELECT COALESCE(SUM(CAST(haber AS REAL)), 0) AS total "
        "FROM ledger WHERE tipo_movimiento='DISTRIBUCION_INVERSOR' AND correlacion_id=?",
        (correlacion,),
      )
      assert cobrado["total"] == pytest.approx(150.0)
      assert distribuido["total"] == pytest.approx(150.0)
    finally: db.close()


def test_fallo_recalculo_revierte_pago_y_eventos(tmp_path):
    db=DB(tmp_path/'d.db'); setup(db)
    try:
      db.conn.execute("CREATE TRIGGER rompe BEFORE INSERT ON historial_recalculos BEGIN SELECT RAISE(ABORT,'falla recalc'); END;")
      with pytest.raises(sqlite3.IntegrityError,match='falla recalc'):
        factory(db).ejecutar(cmd(idempotency_key='rollback'))
      assert db.consultar_uno('SELECT COUNT(*) n FROM pagos')['n']==0
      assert db.consultar_uno('SELECT COUNT(*) n FROM devengamientos')['n']==0
      assert db.consultar_uno('SELECT COUNT(*) n FROM historial_recalculos')['n']==0
      assert db.consultar_uno("SELECT COUNT(*) n FROM cuotas WHERE estado='REESTRUCTURADA'")['n']==0
      assert db.consultar_uno('SELECT revision_prestamo FROM prestamos WHERE id=1')['revision_prestamo']==0
    finally: db.close()


def test_exceso_sin_opcion_es_error(tmp_path):
    db=DB(tmp_path/'e.db'); setup(db)
    try:
      with pytest.raises(ErrorValidacion,match='RAI o RNI'):
        factory(db).ejecutar(cmd(opcion_adelanto=None,idempotency_key='no-option'))
    finally: db.close()


def test_opcion_sin_exceso_es_error(tmp_path):
    db=DB(tmp_path/'f.db'); setup(db)
    try:
      with pytest.raises(ErrorValidacion,match='No existe excedente'):
        factory(db).ejecutar(cmd(monto=Decimal('100'),idempotency_key='no-excess'))
    finally: db.close()
