"""Adaptador SQLite para la consulta del listado de préstamos.

La capa de infraestructura traduce los repositorios existentes al contrato
pequeño que usa la aplicación. No aplica filtros de presentación ni escribe
datos.
"""
from __future__ import annotations

from aplicacion.consultas.listado_prestamos import (
    CuotaProximaListado,
    ParticipacionListado,
    PrestamoListado,
)
from infraestructura.repositorios import ParticipacionRepo, PrestamoRepo


class ListadoPrestamosSQLite:
    """Obtiene los datos de lectura usando los repositorios actuales."""

    def __init__(self, db) -> None:
        self._prestamos = PrestamoRepo(db)
        self._participaciones = ParticipacionRepo(db)

    def prestamos_por_deudor(
        self, persona_id: int
    ) -> tuple[PrestamoListado, ...]:
        return tuple(
            _convertir_prestamo(prestamo)
            for prestamo in self._prestamos.listar(deudor_id=persona_id)
        )

    def participaciones_por_inversor(
        self, persona_id: int
    ) -> tuple[ParticipacionListado, ...]:
        return tuple(
            ParticipacionListado(
                prestamo_id=int(participacion.prestamo_id),
                estado=str(participacion.estado),
                capital_aportado=participacion.capital_aportado,
            )
            for participacion in self._participaciones.por_inversor(persona_id)
        )

    def prestamo_por_id(self, prestamo_id: int) -> PrestamoListado | None:
        prestamo = self._prestamos.obtener(prestamo_id)
        return None if prestamo is None else _convertir_prestamo(prestamo)

    def proxima_cuota(
        self, prestamo_id: int
    ) -> CuotaProximaListado | None:
        version_id = self._prestamos.version_activa(prestamo_id)
        if version_id is None:
            return None

        # La consulta mantiene el orden por número de cuota del repositorio.
        # Se muestra la primera cuyo estado sigue siendo PENDIENTE.
        for cuota in self._prestamos.cuotas(version_id):
            if cuota.estado == "PENDIENTE":
                return CuotaProximaListado(
                    estado=str(cuota.estado),
                    fecha_vencimiento=cuota.fecha_vencimiento,
                )
        return None


def _convertir_prestamo(prestamo) -> PrestamoListado:
    """Evita exponer los modelos concretos del repositorio a la aplicación."""
    return PrestamoListado(
        id=int(prestamo.id),
        numero=str(prestamo.numero),
        estado=str(prestamo.estado),
        fecha_inicio=prestamo.fecha_inicio,
        destino=prestamo.destino,
        capital_original=prestamo.capital_original,
    )


__all__ = ["ListadoPrestamosSQLite"]
