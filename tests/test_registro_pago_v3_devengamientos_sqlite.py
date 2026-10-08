from datetime import date
from decimal import Decimal
import pytest

from aplicacion.comandos import RegistrarPagoCommand
from aplicacion.servicios.fabrica_registro_pago_v3 import crear_registrador_pago_v3_con_devengamientos
from dominio.tipos import ConvencionDias, ModalidadTasa
from infraestructura.migraciones.v010_devengamientos_v3 import aplicar
from tests.test_registro_pago_v3_sqlite import DB, setup


def setup_g3(db):
    setup(db)
    class W:
        def ejecutar(self, sql, params=()): return db.conn.execute(sql, params)
    aplicar(W())
    db.conn.commit()


def cmd(**changes):
    data={'prestamo_id':1,'monto':Decimal('10'),'fecha_real':date(2026,11,11),'usuario':'admin'}
    data.update(changes)
    return RegistrarPagoCommand(**data)


def fabrica(db):
    return crear_registrador_pago_v3_con_devengamientos(
        db, tasa_anual=Decimal('0.24'), modalidad_tasa=ModalidadTasa.TNA,
        convencion_dias=ConvencionDias.ACTUAL_365,
    )


def test_registro_persiste_evento_y_referencia_en_la_misma_operacion(tmp_path):
    db=DB(tmp_path/'a.db'); setup_g3(db)
    try:
        r=fabrica(db).ejecutar(cmd(idempotency_key='g3-1'))
        eventos=db.consultar('SELECT * FROM devengamientos WHERE prestamo_id=1 ORDER BY id')
        app=db.consultar_uno("SELECT referencias_devengamiento FROM imputaciones WHERE pago_id=? AND concepto='INTERES'",(r.pago_id,))
        assert len(eventos) == 2
        assert Decimal(eventos[0]['monto']) == Decimal('0.53')
        assert eventos[0]['origen'] == 'INTERES_CAPITAL_PENDIENTE'
        assert Decimal(eventos[1]['monto']) == Decimal('1.37')
        assert eventos[1]['origen'] == 'MORA_CONTRACTUAL'
        assert eventos[0]['referencia'] in app['referencias_devengamiento']
    finally: db.close()


def test_repeticion_no_duplica_evento(tmp_path):
    db=DB(tmp_path/'b.db'); setup_g3(db)
    try:
        caso=fabrica(db); caso.ejecutar(cmd(idempotency_key='idem'))
        r=caso.ejecutar(cmd(idempotency_key='idem'))
        assert r.es_repeticion_idempotente
        assert db.consultar_uno('SELECT COUNT(*) n FROM pagos')['n']==1
        assert db.consultar_uno('SELECT COUNT(*) n FROM devengamientos')['n']==2
    finally: db.close()


def test_segundo_pago_mismo_dia_no_redevenga(tmp_path):
    db=DB(tmp_path/'c.db'); setup_g3(db)
    try:
        caso=fabrica(db)
        caso.ejecutar(cmd(idempotency_key='a'))
        caso.ejecutar(cmd(monto=Decimal('5'), idempotency_key='b'))
        assert db.consultar_uno('SELECT COUNT(*) n FROM devengamientos')['n']==2
        assert db.consultar_uno('SELECT COUNT(*) n FROM pagos')['n']==2
    finally: db.close()


def test_siguiente_periodo_usa_capital_actual(tmp_path):
    db=DB(tmp_path/'d.db'); setup_g3(db)
    try:
        caso=fabrica(db)
        caso.ejecutar(cmd(monto=Decimal('30'), idempotency_key='a'))
        caso.ejecutar(cmd(monto=Decimal('10'), fecha_real=date(2026,11,21), fecha_valor=date(2026,11,21), idempotency_key='b', revision_prestamo=1))
        rows=db.consultar('SELECT base,fecha_desde,fecha_hasta FROM devengamientos ORDER BY id')
        assert len(rows)==3
        assert Decimal(rows[0]['base']) == Decimal('80.00')
        assert Decimal(rows[1]['base']) == Decimal('100.00')
        assert Decimal(rows[2]['base']) == Decimal('71.90')
        assert rows[2]['fecha_desde']=='2026-11-11' and rows[2]['fecha_hasta']=='2026-11-21'
    finally: db.close()


def test_fallo_ledger_revierte_evento_y_pago(tmp_path):
    db=DB(tmp_path/'e.db'); setup_g3(db)
    try:
        db.conn.execute("CREATE TRIGGER romper BEFORE INSERT ON ledger BEGIN SELECT RAISE(ABORT,'fallo g3'); END;")
        with pytest.raises(Exception, match='fallo g3'):
            fabrica(db).ejecutar(cmd(idempotency_key='rb'))
        assert db.consultar_uno('SELECT COUNT(*) n FROM pagos')['n']==0
        assert db.consultar_uno('SELECT COUNT(*) n FROM devengamientos')['n']==0
        assert db.consultar_uno('SELECT revision_prestamo FROM prestamos WHERE id=1')['revision_prestamo']==0
    finally: db.close()


def test_no_persiste_evento_de_obligacion_fuera_del_plan(tmp_path):
    db=DB(tmp_path/'f.db'); setup_g3(db)
    try:
        db.conn.execute("UPDATE cuotas SET fecha_vencimiento='2026-11-05', estado='PARCIAL', tuvo_pago_parcial=1, interes_pendiente='0', capital_pendiente='100' WHERE id=2")
        db.conn.commit()
        fabrica(db).ejecutar(cmd(idempotency_key='only-first'))
        rows=db.consultar('SELECT cuota_id FROM devengamientos ORDER BY id')
        assert [r['cuota_id'] for r in rows]==[1, 1]
    finally: db.close()
