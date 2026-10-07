from datetime import date
from decimal import Decimal
import sqlite3
from pathlib import Path

import pytest

from dominio.devengamiento_v3 import PoliticaInteres
from dominio.motor_pagos_v3 import Devengamiento
from dominio.tipos import ConceptoImputacion, ConvencionDias, ModalidadTasa
from infraestructura.repositorios.devengamientos_v3 import RepositorioDevengamientosSQLiteV3


class DB:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
    def ejecutar(self, sql, params=()): return self.conn.execute(sql, params)
    def consultar(self, sql, params=()): return self.conn.execute(sql, params).fetchall()
    def consultar_uno(self, sql, params=()): return self.conn.execute(sql, params).fetchone()
    def ultimo_id_insertado(self): return self.conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    def close(self): self.conn.close()


def setup(db: DB):
    db.conn.executescript("""
    CREATE TABLE prestamos (id INTEGER PRIMARY KEY, estado TEXT);
    CREATE TABLE versiones_tasa (id INTEGER PRIMARY KEY, prestamo_id INTEGER);
    CREATE TABLE cuotas (id INTEGER PRIMARY KEY, version_id INTEGER);
    CREATE TABLE devengamientos (
      id INTEGER PRIMARY KEY AUTOINCREMENT, prestamo_id INTEGER NOT NULL, cuota_id INTEGER,
      concepto TEXT NOT NULL, monto TEXT NOT NULL, fecha_desde TEXT NOT NULL, fecha_hasta TEXT NOT NULL,
      origen TEXT NOT NULL, referencia TEXT, base TEXT NOT NULL, tasa_anual TEXT NOT NULL,
      modalidad_tasa TEXT, convencion_dias TEXT, dias INTEGER NOT NULL DEFAULT 0,
      fraccion_anual TEXT NOT NULL DEFAULT '0', huella TEXT NOT NULL UNIQUE,
      motor_version TEXT NOT NULL, creado_en TEXT NOT NULL
    );
    CREATE INDEX idx_devengamientos_prestamo_fecha ON devengamientos(prestamo_id, fecha_hasta, id);
    CREATE INDEX idx_devengamientos_cuota_fecha ON devengamientos(cuota_id, fecha_hasta, id);
    CREATE TRIGGER trg_devengamientos_no_update BEFORE UPDATE ON devengamientos BEGIN SELECT RAISE(ABORT,'Los devengamientos son inmutables'); END;
    CREATE TRIGGER trg_devengamientos_no_delete BEFORE DELETE ON devengamientos BEGIN SELECT RAISE(ABORT,'Los devengamientos no se eliminan'); END;
    INSERT INTO prestamos VALUES (1, 'ACTIVO');
    INSERT INTO versiones_tasa VALUES (1, 1);
    INSERT INTO cuotas VALUES (1, 1);
    INSERT INTO cuotas VALUES (2, 1);
    """)
    db.conn.commit()


def dev(fecha1=date(2026,11,1), fecha2=date(2026,12,1), referencia='x'):
    return Devengamiento(
        concepto=ConceptoImputacion.INTERES,
        monto=Decimal('10.00'),
        fecha_desde=fecha1,
        fecha_hasta=fecha2,
        origen='INTERES_CAPITAL_PENDIENTE',
        referencia=referencia,
        base=Decimal('1000.00'),
        tasa_anual=Decimal('0.24'),
        modalidad_tasa=ModalidadTasa.TNA,
        convencion_dias=ConvencionDias.MENSUAL,
        dias=30,
        fraccion_anual=Decimal('0.0833333333333333333333333333'),
    )


def test_registro_y_roundtrip_preserva_evento(tmp_path):
    db=DB(tmp_path/'a.db'); setup(db)
    try:
        repo=RepositorioDevengamientosSQLiteV3(db)
        p=repo.registrar(prestamo_id=1, cuota_id=1, devengamiento=dev())
        assert p.id == 1 and len(p.huella) == 64
        got=repo.por_cuota(1)[0]
        assert got.devengamiento.monto == Decimal('10.00')
        assert got.devengamiento.base == Decimal('1000.00')
        assert got.devengamiento.referencia == 'x'
    finally: db.close()


def test_huella_evita_duplicado_economico(tmp_path):
    db=DB(tmp_path/'b.db'); setup(db)
    try:
        repo=RepositorioDevengamientosSQLiteV3(db); repo.registrar(prestamo_id=1, cuota_id=1, devengamiento=dev())
        with pytest.raises(sqlite3.IntegrityError):
            repo.registrar(prestamo_id=1, cuota_id=1, devengamiento=dev())
    finally: db.close()


def test_no_permite_cuota_de_otro_prestamo(tmp_path):
    db=DB(tmp_path/'c.db'); setup(db)
    db.conn.execute("INSERT INTO prestamos VALUES (2, 'ACTIVO')"); db.conn.commit()
    try:
        repo=RepositorioDevengamientosSQLiteV3(db)
        with pytest.raises(Exception, match='no pertenece'):
            repo.registrar(prestamo_id=2, cuota_id=1, devengamiento=dev())
    finally: db.close()


def test_por_prestamo_hasta_filtra_por_fecha_y_ordena(tmp_path):
    db=DB(tmp_path/'d.db'); setup(db)
    try:
        repo=RepositorioDevengamientosSQLiteV3(db)
        repo.registrar(prestamo_id=1, cuota_id=1, devengamiento=dev(date(2026,11,1), date(2026,12,1),'a'))
        repo.registrar(prestamo_id=1, cuota_id=2, devengamiento=dev(date(2026,12,1), date(2027,1,1),'b'))
        assert len(repo.por_prestamo_hasta(1, date(2026,12,1))) == 1
        assert [x.cuota_id for x in repo.por_prestamo_hasta(1)] == [1,2]
    finally: db.close()


def test_ultimo_hasta_por_cuota_con_filtros(tmp_path):
    db=DB(tmp_path/'e.db'); setup(db)
    try:
        repo=RepositorioDevengamientosSQLiteV3(db)
        repo.registrar(prestamo_id=1, cuota_id=1, devengamiento=dev(date(2026,11,1), date(2026,12,1),'a'))
        assert repo.ultimo_hasta(cuota_id=1) == date(2026,12,1)
        assert repo.ultimo_hasta(cuota_id=1, concepto=ConceptoImputacion.MORA) is None
        assert repo.ultimo_hasta(cuota_id=1, origen='INTERES_CAPITAL_PENDIENTE') == date(2026,12,1)
    finally: db.close()


def test_eventos_son_inmutables(tmp_path):
    db=DB(tmp_path/'f.db'); setup(db)
    try:
        repo=RepositorioDevengamientosSQLiteV3(db)
        repo.registrar(prestamo_id=1, cuota_id=1, devengamiento=dev())
        with pytest.raises(sqlite3.IntegrityError, match='inmutables'):
            db.conn.execute("UPDATE devengamientos SET monto='999' WHERE id=1")
        with pytest.raises(sqlite3.IntegrityError, match='no se eliminan'):
            db.conn.execute("DELETE FROM devengamientos WHERE id=1")
    finally: db.close()


def test_rechaza_monto_cero(tmp_path):
    db=DB(tmp_path/'g.db'); setup(db)
    try:
        repo=RepositorioDevengamientosSQLiteV3(db)
        d=dev(); d=Devengamiento(concepto=d.concepto, monto=Decimal('0'), fecha_desde=d.fecha_desde, fecha_hasta=d.fecha_hasta, origen=d.origen)
        with pytest.raises(Exception, match='cero'):
            repo.registrar(prestamo_id=1, cuota_id=1, devengamiento=d)
    finally: db.close()


def test_busqueda_por_huella(tmp_path):
    db=DB(tmp_path/'h.db'); setup(db)
    try:
        repo=RepositorioDevengamientosSQLiteV3(db)
        p=repo.registrar(prestamo_id=1, cuota_id=1, devengamiento=dev())
        assert repo.por_huella(p.huella).id == p.id
        assert repo.por_huella('x'*64) is None
    finally: db.close()
