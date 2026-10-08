"""Gestor de migraciones."""
from dataclasses import dataclass
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
    from . import v012_ejecuciones_sombra_v3
    from . import v013_configuracion_motor_pago
    from . import v014_auditoria_inmutable
    from . import v015_politica_pago
    from . import v016_politica_pago_en_pago
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
        (12, "ejecuciones_sombra_v3", v012_ejecuciones_sombra_v3.aplicar),
        (13, "configuracion_motor_pago", v013_configuracion_motor_pago.aplicar),
        (14, "auditoria_inmutable", v014_auditoria_inmutable.aplicar),
        (15, "politica_pago", v015_politica_pago.aplicar),
        (16, "politica_pago_en_pago", v016_politica_pago_en_pago.aplicar),
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



@dataclass(frozen=True)
class MigracionPlaneada:
    """Identifica una migración sin ejecutarla."""

    version: int
    nombre: str


@dataclass(frozen=True)
class EstadoMigraciones:
    """Estado leído sin crear tablas ni cambiar el schema."""

    esquema_vacio: bool
    version_actual: int | None
    version_destino: int
    pendientes: tuple[MigracionPlaneada, ...]
    historial_valido: bool
    detalle: str | None = None

    @property
    def es_base_nueva(self) -> bool:
        """Indica que no hay tablas de aplicación ni historial aplicado."""
        return self.esquema_vacio and self.historial_valido


def version_destino_migraciones() -> int:
    """Devuelve la última versión declarada por el código."""
    return max((version for version, _, _ in _cargar_migraciones()), default=0)


def inspeccionar_estado_migraciones(db: BaseDatos) -> EstadoMigraciones:
    """Inspecciona el historial sin crear la tabla `migraciones`.

    Una base existente sin historial, con versiones desconocidas o con saltos
    en la secuencia se marca como inválida para evitar que el programa adivine
    qué cambios económicos o estructurales ya se aplicaron.
    """
    tablas = {
        fila["name"]
        for fila in db.consultar(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    esquema_sin_datos_de_migracion = tablas - {"migraciones"}
    tiene_tabla_historial = "migraciones" in tablas
    filas = (
        db.consultar("SELECT version, nombre FROM migraciones ORDER BY version")
        if tiene_tabla_historial
        else []
    )
    aplicadas = {int(fila["version"]) for fila in filas}
    todas = tuple(
        MigracionPlaneada(version, nombre)
        for version, nombre, _ in _cargar_migraciones()
    )
    versiones_conocidas = {m.version for m in todas}
    version_destino = max(versiones_conocidas, default=0)
    version_origen = max(aplicadas, default=0)
    pendientes = tuple(m for m in todas if m.version not in aplicadas)
    esquema_vacio = not esquema_sin_datos_de_migracion and not aplicadas

    if not tiene_tabla_historial:
        if esquema_vacio:
            return EstadoMigraciones(
                esquema_vacio=True,
                version_actual=0,
                version_destino=version_destino,
                pendientes=pendientes,
                historial_valido=True,
            )
        return EstadoMigraciones(
            esquema_vacio=False,
            version_actual=None,
            version_destino=version_destino,
            pendientes=pendientes,
            historial_valido=False,
            detalle=(
                "La base contiene tablas pero no tiene historial de migraciones. "
                "Se requiere revisión explícita; no se aplicaron cambios."
            ),
        )

    desconocidas = sorted(aplicadas - versiones_conocidas)
    if desconocidas:
        detalle = (
            "El historial contiene versiones que este código no reconoce: "
            + ", ".join(str(v) for v in desconocidas)
        )
        valido = False
    elif aplicadas != set(range(1, version_origen + 1)):
        detalle = (
            "El historial de migraciones tiene saltos o versiones ausentes; "
            "no se puede calcular una actualización segura."
        )
        valido = False
    elif not aplicadas and esquema_sin_datos_de_migracion:
        detalle = (
            "La base contiene tablas de aplicación, pero no registra "
            "migraciones aplicadas."
        )
        valido = False
    else:
        detalle = None
        valido = True

    return EstadoMigraciones(
        esquema_vacio=esquema_vacio,
        version_actual=version_origen,
        version_destino=version_destino,
        pendientes=pendientes,
        historial_valido=valido,
        detalle=detalle,
    )


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
