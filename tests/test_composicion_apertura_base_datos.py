"""Pruebas de la composición segura de apertura de la base local."""

from datetime import datetime
from pathlib import Path

import pytest

from infraestructura import BaseDatos
from infraestructura.excepciones import ErrorConexion
from infraestructura.migraciones import (
    inspeccionar_estado_migraciones,
    version_destino_migraciones,
)
from infraestructura.migraciones.gestor import (
    _asegurar_tabla_migraciones,
    _cargar_migraciones,
)
from infraestructura.composicion.apertura_base_datos import (
    EstadoAperturaBaseDatos,
    abrir_base_datos_para_aplicacion,
)
import infraestructura.composicion.apertura_base_datos as composicion


def _crear_base_en_version(ruta: Path, version_objetivo: int) -> None:
    """Construye un schema histórico aplicando solo las versiones indicadas."""
    with BaseDatos(ruta) as db:
        _asegurar_tabla_migraciones(db)
        for version, nombre, migrar in _cargar_migraciones():
            if version > version_objetivo:
                break
            with db.transaccion():
                migrar(db)
                db.ejecutar(
                    """
                    INSERT INTO migraciones (version, nombre, aplicada_en)
                    VALUES (?, ?, ?)
                    """,
                    (version, nombre, datetime(2026, 11, 26).isoformat()),
                )


def test_base_nueva_se_inicializa_y_se_entrega_abierta(tmp_path: Path) -> None:
    ruta = tmp_path / "nueva.db"

    resultado = abrir_base_datos_para_aplicacion(ruta)

    assert resultado.estado is EstadoAperturaBaseDatos.DISPONIBLE
    assert resultado.db is not None
    assert resultado.estado_migraciones is not None
    assert resultado.estado_migraciones.es_base_nueva is False
    assert resultado.estado_migraciones.historial_valido is True
    assert resultado.estado_migraciones.version_actual == version_destino_migraciones()
    assert resultado.estado_migraciones.pendientes == ()
    assert resultado.db.verificar_integridad_completa() is True
    resultado.db.cerrar()


def test_base_existente_actualizada_se_entrega_abierta_sin_reaplicar(
    tmp_path: Path,
) -> None:
    ruta = tmp_path / "actualizada.db"
    _crear_base_en_version(ruta, version_destino_migraciones())

    resultado = abrir_base_datos_para_aplicacion(ruta)

    assert resultado.estado is EstadoAperturaBaseDatos.DISPONIBLE
    assert resultado.db is not None
    assert resultado.estado_migraciones is not None
    assert resultado.estado_migraciones.pendientes == ()
    assert resultado.estado_migraciones.version_actual == version_destino_migraciones()
    resultado.db.cerrar()


def test_base_existente_con_migraciones_pendientes_se_cierra_sin_modificar(
    tmp_path: Path,
) -> None:
    ruta = tmp_path / "historica.db"
    version_origen = version_destino_migraciones() - 1
    _crear_base_en_version(ruta, version_origen)

    resultado = abrir_base_datos_para_aplicacion(ruta)

    assert resultado.estado is EstadoAperturaBaseDatos.MIGRACION_PENDIENTE
    assert resultado.db is None
    assert resultado.estado_migraciones is not None
    assert resultado.estado_migraciones.version_actual == version_origen
    assert [m.version for m in resultado.estado_migraciones.pendientes] == [
        version_origen + 1
    ]

    # La UI no dejó una conexión abierta ni aplicó la migración pendiente.
    with BaseDatos(ruta) as db:
        estado = inspeccionar_estado_migraciones(db)
    assert estado.version_actual == version_origen
    assert [m.version for m in estado.pendientes] == [version_origen + 1]


def test_historial_invalido_se_rechaza_y_no_entrega_conexion(
    tmp_path: Path,
) -> None:
    ruta = tmp_path / "sin-historial.db"
    with BaseDatos(ruta) as db:
        db.ejecutar("CREATE TABLE hechos_anteriores (id INTEGER PRIMARY KEY)")

    resultado = abrir_base_datos_para_aplicacion(ruta)

    assert resultado.estado is EstadoAperturaBaseDatos.HISTORIAL_INVALIDO
    assert resultado.db is None
    assert resultado.estado_migraciones is not None
    assert resultado.estado_migraciones.historial_valido is False

    with BaseDatos(ruta) as db:
        tablas = {
            fila["name"]
            for fila in db.consultar(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "hechos_anteriores" in tablas
    assert "migraciones" not in tablas


def test_error_de_inspeccion_cierra_la_conexion_abierta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    conexiones: list[BaseDatos] = []

    class BaseDatosObservada(BaseDatos):
        def __init__(self, ruta):
            super().__init__(ruta)
            conexiones.append(self)

    def fallar_inspeccion(_db):
        raise RuntimeError("fallo de inspección simulado")

    monkeypatch.setattr(composicion, "BaseDatos", BaseDatosObservada)
    monkeypatch.setattr(composicion, "inspeccionar_estado_migraciones", fallar_inspeccion)

    resultado = composicion.abrir_base_datos_para_aplicacion(
        tmp_path / "inspeccion-fallida.db"
    )

    assert resultado.estado is EstadoAperturaBaseDatos.ERROR_INSPECCION
    assert resultado.db is None
    assert "fallo de inspección simulado" in (resultado.error or "")
    assert len(conexiones) == 1
    with pytest.raises(ErrorConexion):
        conexiones[0].consultar("SELECT 1")


def test_fallo_al_inicializar_base_nueva_cierra_la_conexion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    conexiones: list[BaseDatos] = []

    class BaseDatosObservada(BaseDatos):
        def __init__(self, ruta):
            super().__init__(ruta)
            conexiones.append(self)

    def fallar_migraciones(_db):
        raise RuntimeError("fallo de migración simulado")

    monkeypatch.setattr(composicion, "BaseDatos", BaseDatosObservada)
    monkeypatch.setattr(composicion, "aplicar_migraciones", fallar_migraciones)

    resultado = composicion.abrir_base_datos_para_aplicacion(
        tmp_path / "inicializacion-fallida.db"
    )

    assert resultado.estado is EstadoAperturaBaseDatos.ERROR_INICIALIZACION
    assert resultado.db is None
    assert "fallo de migración simulado" in (resultado.error or "")
    assert len(conexiones) == 1
    with pytest.raises(ErrorConexion):
        conexiones[0].consultar("SELECT 1")


def test_no_entrega_base_nueva_si_la_verificacion_final_deja_pendientes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un runner que no complete el schema nunca entrega la conexión a la UI."""
    conexiones: list[BaseDatos] = []

    class BaseDatosObservada(BaseDatos):
        def __init__(self, ruta):
            super().__init__(ruta)
            conexiones.append(self)

    monkeypatch.setattr(composicion, "BaseDatos", BaseDatosObservada)
    monkeypatch.setattr(composicion, "aplicar_migraciones", lambda _db: [])

    resultado = composicion.abrir_base_datos_para_aplicacion(
        tmp_path / "schema-incompleto.db"
    )

    assert resultado.estado is EstadoAperturaBaseDatos.ERROR_VERIFICACION_FINAL
    assert resultado.db is None
    assert resultado.estado_migraciones is not None
    assert resultado.estado_migraciones.pendientes
    assert len(conexiones) == 1
    with pytest.raises(ErrorConexion):
        conexiones[0].consultar("SELECT 1")
