"""Lectura SQLite de los datos del resumen financiero principal.

Aquí se consultan repositorios y la versión de tasa necesaria. La fórmula y
los mensajes que explican el resultado viven en aplicación, no en este
adaptador de lectura.
"""
from __future__ import annotations

from decimal import Decimal

from aplicacion.consultas.metricas_principales import DatosMetricasPrincipales
from infraestructura.db import BaseDatos
from infraestructura.repositorios import ParticipacionRepo, PrestamoRepo


ESTADOS_PRESTAMO_ACTIVO = ("ACTIVO", "EN_MORA")
ESTADOS_CUOTA_PENDIENTE = ("PENDIENTE", "PARCIAL", "VENCIDA")


class LectorMetricasPrincipales:
    """Obtiene, desde SQLite, los datos requeridos por el cálculo principal."""

    def __init__(self, db: BaseDatos) -> None:
        self._db = db
        self._participaciones = ParticipacionRepo(db)
        self._prestamos = PrestamoRepo(db)

    def obtener(self, persona_id: int) -> DatosMetricasPrincipales:
        """Devuelve capital invertido, deuda pendiente y tasa de referencia."""
        participaciones = self._participaciones.por_inversor(persona_id)
        capital_invertido = sum(
            (
                participacion.capital_aportado
                for participacion in participaciones
                if participacion.estado == "ACTIVA"
            ),
            Decimal("0"),
        )

        prestamos_como_deudor = self._prestamos.listar(
            deudor_id=persona_id
        )
        capital_adeudado = Decimal("0")
        for prestamo in prestamos_como_deudor:
            if prestamo.estado not in ESTADOS_PRESTAMO_ACTIVO:
                continue

            version_id = self._prestamos.version_activa(prestamo.id)
            if version_id is None:
                continue

            cuotas = self._prestamos.cuotas(version_id)
            cuotas_pendientes = [
                cuota
                for cuota in cuotas
                if cuota.estado in ESTADOS_CUOTA_PENDIENTE
            ]
            # Se conserva el criterio actual de la pantalla: tomar el capital
            # inicial de la primera cuota pendiente de cada préstamo activo.
            if cuotas_pendientes:
                capital_adeudado += cuotas_pendientes[0].capital_inicial

        tasa_anual = None
        modalidad_tasa = None
        if capital_adeudado > 0 and prestamos_como_deudor:
            # Mantiene la selección de tasa vigente: el primer préstamo activo
            # de la lista, no una tasa nueva elegida por este adaptador.
            prestamo_activo = next(
                (
                    prestamo
                    for prestamo in prestamos_como_deudor
                    if prestamo.estado in ESTADOS_PRESTAMO_ACTIVO
                ),
                None,
            )
            if prestamo_activo:
                version_id = self._prestamos.version_activa(
                    prestamo_activo.id
                )
                if version_id is not None:
                    fila = self._db.consultar_uno(
                        "SELECT tasa_anual, modalidad_tasa "
                        "FROM versiones_tasa WHERE id = ?",
                        (version_id,),
                    )
                    if fila:
                        tasa_anual = Decimal(fila["tasa_anual"])
                        modalidad_tasa = fila["modalidad_tasa"]

        return DatosMetricasPrincipales(
            capital_invertido=capital_invertido,
            capital_adeudado=capital_adeudado,
            tasa_anual=tasa_anual,
            modalidad_tasa=modalidad_tasa,
        )


__all__ = ["LectorMetricasPrincipales"]
