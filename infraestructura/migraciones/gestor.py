"""Gestor de migraciones."""
from datetime import datetime

from ..db import BaseDatos
from ..excepciones import ErrorMigracion


def _cargar_migraciones() -> list[tuple[int, str, callable]]:
    from . import v001_inicial
    from . import v002_monto_pendiente
    from . import v003_pendientes_desglosados
    from . import v004_pagos_adelantos
    from . import v005_tuvo_pago_parcial
    from . import v006_interes_extra_generado
    from . import v007_cuota_objetivo_recalculo
    from . import v008_fue_recalculada
    from . import v009_registro_pago_v3
    from . import v010_devengamientos_v3
    from . import v011_observaciones_sombra_v3
    return [
        (1, "inicial", v001_inicial.aplicar),
        (2, "monto_pendiente", v002_monto_pendiente.aplicar),
        (3, "pendientes_desglosados", v003_pendientes_desglosados.aplicar),
        (4, "pagos_adelantos", v004_pagos_adelantos.aplicar),
        (5, "tuvo_pago_parcial", v005_tuvo_pago_parcial.aplicar),
        (6, "interes_extra_generado", v006_interes_extra_generado.aplicar),
        (7, "cuota_objetivo_recalculo", v007_cuota_objetivo_recalculo.aplicar),
        (8, "fue_recalculada", v008_fue_recalculada.aplicar),
        (9, "registro_pago_v3", v009_registro_pago_v3.aplicar),
        (10, "devengamientos_v3", v010_devengamientos_v3.aplicar),
        (11, "observaciones_sombra_v3", v011_observaciones_sombra_v3.aplicar),
    ]


def _asegurar_tabla_migraciones(db: BaseDatos) -> None:
    db.ejecutar("""
        CREATE TABLE IF NOT EXISTS migraciones (
            version INTEGER PRIMARY KEY, nombre TEXT NOT NULL,
            aplicada_en TEXT NOT NULL, hash TEXT
        )
    """)


def _migraciones_aplicadas(db: BaseDatos) -> set[int]:
    filas = db.consultar("SELECT version FROM migraciones")
    return {fila["version"] for fila in filas}


def version_actual(db: BaseDatos) -> int:
    _asegurar_tabla_migraciones(db)
    fila = db.consultar_uno("SELECT MAX(version) AS v FROM migraciones")
    if fila is None or fila["v"] is None:
        return 0
    return fila["v"]


def aplicar_migraciones(db: BaseDatos) -> list[int]:
    _asegurar_tabla_migraciones(db)
    ya_aplicadas = _migraciones_aplicadas(db)
    todas = _cargar_migraciones()
    pendientes = [(v, n, fn) for v, n, fn in todas if v not in ya_aplicadas]
    pendientes.sort(key=lambda x: x[0])
    aplicadas_ahora = []
    for version, nombre, funcion in pendientes:
        try:
            with db.transaccion():
                funcion(db)
                db.ejecutar(
                    "INSERT INTO migraciones (version, nombre, aplicada_en) VALUES (?, ?, ?)",
                    (version, nombre, datetime.now().isoformat()),
                )
            aplicadas_ahora.append(version)
        except Exception as e:
            raise ErrorMigracion(f"Falló la migración v{version:03d} ({nombre}): {e}") from e
    return aplicadas_ahora
