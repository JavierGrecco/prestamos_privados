"""Pruebas de la frontera operativa consumida por Streamlit."""

from pathlib import Path

import pytest

from aplicacion.servicios.operacion_ui import ServicioOperacionUI
from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones
from infraestructura.excepciones import ErrorBackup


def _db(tmp_path: Path) -> BaseDatos:
    db = BaseDatos(tmp_path / "prestamos.db")
    db.abrir()
    aplicar_migraciones(db)
    return db


def test_integridad_y_listado_de_backups_sin_efectos_financieros(tmp_path: Path):
    db = _db(tmp_path)
    try:
        servicio = ServicioOperacionUI(db)
        resultado = servicio.verificar_integridad()

        assert resultado.ok is True
        assert servicio.listar_backups() == ()
        assert db.consultar_uno("SELECT MAX(version) AS v FROM migraciones")["v"] == 12
    finally:
        db.cerrar()


def test_backup_requiere_confirmacion_explicita(tmp_path: Path):
    db = _db(tmp_path)
    try:
        servicio = ServicioOperacionUI(db)

        with pytest.raises(ValueError, match="confirmación explícita"):
            servicio.crear_backup(confirmar=False)

        assert not servicio.directorio_backups.exists()
    finally:
        db.cerrar()


def test_crea_verifica_y_lista_backup(tmp_path: Path):
    db = _db(tmp_path)
    try:
        servicio = ServicioOperacionUI(db)
        resultado = servicio.crear_backup(confirmar=True)

        assert resultado.integridad.ok is True
        assert resultado.ruta_backup.parent == servicio.directorio_backups
        assert resultado.ruta_backup in servicio.listar_backups()

        verificado = servicio.verificar_backup(resultado.ruta_backup)
        assert verificado.sha256 == resultado.sha256
    finally:
        db.cerrar()


def test_restore_drill_no_expone_ni_modifica_la_base_activa(tmp_path: Path):
    db = _db(tmp_path)
    try:
        servicio = ServicioOperacionUI(db)
        backup = servicio.crear_backup(confirmar=True)
        before = db.consultar_uno("SELECT MAX(version) AS v FROM migraciones")

        drill = servicio.ejecutar_restore_drill(backup.ruta_backup)

        assert drill.ok is True
        assert drill.sha256 == backup.sha256
        assert drill.bytes == backup.bytes
        assert servicio.directorio_backups.exists()
        assert db.consultar_uno("SELECT MAX(version) AS v FROM migraciones")["v"] == before["v"]
    finally:
        db.cerrar()


def test_rechaza_backup_fuera_del_directorio_operativo(tmp_path: Path):
    db = _db(tmp_path)
    try:
        servicio = ServicioOperacionUI(db)
        externo = tmp_path / "otro.db"
        externo.write_bytes(b"no es un backup operativo")

        with pytest.raises(ValueError, match="directorio operativo"):
            servicio.verificar_backup(externo)
        with pytest.raises(ValueError, match="directorio operativo"):
            servicio.ejecutar_restore_drill(externo)
    finally:
        db.cerrar()
