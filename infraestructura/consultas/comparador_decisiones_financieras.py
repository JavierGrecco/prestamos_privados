"""Adaptador SQLite para datos de alternativas del comparador M7."""

from __future__ import annotations

from decimal import Decimal

from aplicacion.puertos.comparador_decisiones_financieras import (
    ParticipacionComparadorLectura,
    PrestamoComparadorLectura,
    TasaActivaComparadorLectura,
)
from infraestructura.repositorios import ParticipacionRepo, PersonaRepo, PrestamoRepo


class ComparadorDecisionesFinancierasSQLiteQuery:
    """Resuelve las lecturas del comparador mediante repositorios existentes."""

    def __init__(self, db) -> None:
        self._personas = PersonaRepo(db)
        self._prestamos = PrestamoRepo(db)
        self._participaciones = ParticipacionRepo(db)

    def persona_existe(self, persona_id: int) -> bool:
        return self._personas.obtener(persona_id) is not None

    def prestamos_por_deudor(
        self, persona_id: int
    ) -> tuple[PrestamoComparadorLectura, ...]:
        return tuple(
            _prestamo_a_lectura(prestamo)
            for prestamo in self._prestamos.listar(deudor_id=persona_id)
            if prestamo.id is not None
        )

    def participaciones_por_inversor(
        self, persona_id: int
    ) -> tuple[ParticipacionComparadorLectura, ...]:
        return tuple(
            ParticipacionComparadorLectura(
                prestamo_id=int(participacion.prestamo_id),
                estado=str(participacion.estado),
                capital_aportado=Decimal(str(participacion.capital_aportado)),
                porcentaje=Decimal(str(participacion.porcentaje)),
            )
            for participacion in self._participaciones.por_inversor(persona_id)
        )

    def prestamo_por_id(
        self, prestamo_id: int
    ) -> PrestamoComparadorLectura | None:
        prestamo = self._prestamos.obtener(prestamo_id)
        if prestamo is None or prestamo.id is None:
            return None
        return _prestamo_a_lectura(prestamo)

    def tasa_activa(
        self, prestamo_id: int
    ) -> TasaActivaComparadorLectura | None:
        tasa = self._prestamos.info_tasa_activa(prestamo_id)
        if tasa is None:
            return None
        return TasaActivaComparadorLectura(
            tasa_anual=Decimal(str(tasa["tasa_anual"])),
            modalidad=str(tasa["modalidad"]),
        )


def _prestamo_a_lectura(prestamo) -> PrestamoComparadorLectura:
    """Evita exponer el modelo de persistencia fuera de infraestructura."""
    return PrestamoComparadorLectura(
        id=int(prestamo.id),
        numero=str(prestamo.numero),
        destino=prestamo.destino,
        estado=str(prestamo.estado),
        capital_original=Decimal(str(prestamo.capital_original)),
        moneda_contractual=str(prestamo.moneda_contractual),
        sistema=str(prestamo.sistema),
        convencion_dias=str(prestamo.convencion_dias),
        fecha_inicio=prestamo.fecha_inicio,
    )


__all__ = ["ComparadorDecisionesFinancierasSQLiteQuery"]
