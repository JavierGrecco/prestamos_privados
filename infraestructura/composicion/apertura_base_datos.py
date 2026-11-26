"""Composición del ciclo de vida inicial de la base local.

La UI solo presenta el resultado. La apertura, la inspección del historial y
la inicialización de una base nueva pertenecen a infraestructura/composicion.
Las bases existentes con migraciones pendientes se cierran y requieren el
comando explícito de migración con backup verificado.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from infraestructura.db import BaseDatos
from infraestructura.migraciones import (
    EstadoMigraciones,
    aplicar_migraciones,
    inspeccionar_estado_migraciones,
)


class EstadoAperturaBaseDatos(str, Enum):
    """Resultado seguro del intento de preparar la base para la aplicación."""

    DISPONIBLE = "DISPONIBLE"
    ERROR_APERTURA = "ERROR_APERTURA"
    ERROR_INSPECCION = "ERROR_INSPECCION"
    HISTORIAL_INVALIDO = "HISTORIAL_INVALIDO"
    ERROR_INICIALIZACION = "ERROR_INICIALIZACION"
    MIGRACION_PENDIENTE = "MIGRACION_PENDIENTE"
    ERROR_VERIFICACION_FINAL = "ERROR_VERIFICACION_FINAL"


@dataclass(frozen=True)
class ResultadoAperturaBaseDatos:
    """Base abierta solo cuando el estado permite operar con seguridad."""

    estado: EstadoAperturaBaseDatos
    db: BaseDatos | None = None
    estado_migraciones: EstadoMigraciones | None = None
    error: str | None = None


def _cerrar(db: BaseDatos | None) -> None:
    """Cierra la conexión si llegó a abrirse, incluso ante fallos de inspección."""
    if db is None:
        return
    try:
        db.cerrar()
    except Exception:
        # El error principal ya se conserva en ResultadoAperturaBaseDatos.
        # No devolver una conexión dudosa a la UI es más importante que
        # propagar un segundo error durante el cierre de emergencia.
        pass


def _error(exc: Exception) -> str:
    """Devuelve un detalle técnico sin incorporar datos financieros."""
    return f"{type(exc).__name__}: {exc}"


def abrir_base_datos_para_aplicacion(
    ruta: str | Path,
) -> ResultadoAperturaBaseDatos:
    """Prepara la base local y nunca entrega una conexión con schema incompleto.

    - Base nueva: la inicializa y vuelve a comprobar la versión final.
    - Base existente actualizada: la entrega abierta.
    - Base existente con migraciones pendientes: la cierra y exige el CLI.
    - Historial inválido o fallo de migración: la cierra y devuelve un estado
      que la UI debe mostrar sin continuar con el resto de la aplicación.
    """
    db: BaseDatos | None = None
    try:
        db = BaseDatos(ruta)
        db.abrir()
    except Exception as exc:
        _cerrar(db)
        return ResultadoAperturaBaseDatos(
            estado=EstadoAperturaBaseDatos.ERROR_APERTURA,
            error=_error(exc),
        )

    try:
        estado = inspeccionar_estado_migraciones(db)
    except Exception as exc:
        _cerrar(db)
        return ResultadoAperturaBaseDatos(
            estado=EstadoAperturaBaseDatos.ERROR_INSPECCION,
            error=_error(exc),
        )

    if not estado.historial_valido:
        _cerrar(db)
        return ResultadoAperturaBaseDatos(
            estado=EstadoAperturaBaseDatos.HISTORIAL_INVALIDO,
            estado_migraciones=estado,
            error=estado.detalle,
        )

    if estado.es_base_nueva:
        try:
            aplicar_migraciones(db)
        except Exception as exc:
            _cerrar(db)
            return ResultadoAperturaBaseDatos(
                estado=EstadoAperturaBaseDatos.ERROR_INICIALIZACION,
                estado_migraciones=estado,
                error=_error(exc),
            )

        try:
            estado_final = inspeccionar_estado_migraciones(db)
        except Exception as exc:
            _cerrar(db)
            return ResultadoAperturaBaseDatos(
                estado=EstadoAperturaBaseDatos.ERROR_VERIFICACION_FINAL,
                error=_error(exc),
            )

        if not estado_final.historial_valido or estado_final.pendientes:
            _cerrar(db)
            return ResultadoAperturaBaseDatos(
                estado=EstadoAperturaBaseDatos.ERROR_VERIFICACION_FINAL,
                estado_migraciones=estado_final,
                error=(
                    estado_final.detalle
                    or "La base nueva no alcanzó la versión de schema esperada."
                ),
            )

        return ResultadoAperturaBaseDatos(
            estado=EstadoAperturaBaseDatos.DISPONIBLE,
            db=db,
            estado_migraciones=estado_final,
        )

    if estado.pendientes:
        _cerrar(db)
        return ResultadoAperturaBaseDatos(
            estado=EstadoAperturaBaseDatos.MIGRACION_PENDIENTE,
            estado_migraciones=estado,
        )

    return ResultadoAperturaBaseDatos(
        estado=EstadoAperturaBaseDatos.DISPONIBLE,
        db=db,
        estado_migraciones=estado,
    )


__all__ = [
    "EstadoAperturaBaseDatos",
    "ResultadoAperturaBaseDatos",
    "abrir_base_datos_para_aplicacion",
]
