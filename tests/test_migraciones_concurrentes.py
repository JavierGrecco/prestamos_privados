"""Dos procesos de arranque no deben aplicar dos veces la misma migración."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from infraestructura import BaseDatos
from infraestructura.migraciones import aplicar_migraciones, inspeccionar_estado_migraciones, version_destino_migraciones


def test_dos_conexiones_inicializando_una_base_aplican_migraciones_una_sola_vez(
    tmp_path: Path,
) -> None:
    ruta = tmp_path / "inicio-concurrente.db"
    db1 = BaseDatos(ruta)
    db2 = BaseDatos(ruta)
    db1.abrir()
    db2.abrir()
    salida = Barrier(2, timeout=10)

    def inicializar(db: BaseDatos) -> list[int]:
        salida.wait()
        return aplicar_migraciones(db)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futuro1 = pool.submit(inicializar, db1)
            futuro2 = pool.submit(inicializar, db2)
            resultado1 = futuro1.result(timeout=30)
            resultado2 = futuro2.result(timeout=30)

        aplicadas = resultado1 + resultado2
        assert sorted(aplicadas) == list(range(1, version_destino_migraciones() + 1))
        assert len(aplicadas) == version_destino_migraciones()
        assert len(set(aplicadas)) == version_destino_migraciones()

        estado = inspeccionar_estado_migraciones(db1)
        assert estado.historial_valido is True
        assert estado.version_actual == estado.version_destino == version_destino_migraciones()
        assert estado.pendientes == ()
        assert db1.consultar("PRAGMA foreign_key_check") == []
        assert db1.verificar_integridad_completa() is True
    finally:
        db2.cerrar()
        db1.cerrar()
