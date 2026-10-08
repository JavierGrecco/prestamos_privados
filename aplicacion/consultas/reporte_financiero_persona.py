"""Read model consolidado para reportes financieros de una persona.

Este módulo únicamente compone read models existentes. No recalcula reglas
financieras ni modifica datos persistidos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aplicacion.consultas.escenarios_persona import (
    ResultadoEscenariosPersona,
    ServicioEscenariosPersona,
)
from aplicacion.consultas.planificacion_financiera_persona import (
    PlanificacionFinancieraPersona,
    ServicioPlanificacionFinancieraPersona,
)
from aplicacion.consultas.posicion_financiera_persona import (
    PosicionFinancieraPersona,
    ServicioPosicionFinancieraPersona,
)
from aplicacion.consultas.rendimiento_financiero_persona import (
    RendimientoFinancieroPersona,
    ServicioRendimientoFinancieroPersona,
)
from infraestructura.db import BaseDatos
from infraestructura.repositorios import PersonaRepo


@dataclass(frozen=True)
class ReporteFinancieroPersona:
    persona_id: int
    nombre_persona: str
    fecha_corte: date
    inflacion_mensual_supuesta: Decimal
    horizonte_meses: int
    posicion: PosicionFinancieraPersona
    planificacion: PlanificacionFinancieraPersona
    escenarios: ResultadoEscenariosPersona
    rendimiento: RendimientoFinancieroPersona


class ReporteFinancieroPersonaQuery:
    """Compone toda la información financiera conocida de una persona."""

    def __init__(self, db: BaseDatos) -> None:
        self._personas = PersonaRepo(db)
        self._posicion = ServicioPosicionFinancieraPersona(db)
        self._planificacion = ServicioPlanificacionFinancieraPersona(db)
        self._escenarios = ServicioEscenariosPersona(db)
        self._rendimiento = ServicioRendimientoFinancieroPersona(db)

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        inflacion_mensual_supuesta: Decimal = Decimal("0.05"),
        horizonte_meses: int = 12,
    ) -> ReporteFinancieroPersona:
        persona = self._personas.obtener(persona_id)
        if persona is None:
            raise ValueError(f"La persona {persona_id} no existe")

        if horizonte_meses < 1 or horizonte_meses > 60:
            raise ValueError("horizonte_meses debe estar entre 1 y 60")

        corte = fecha_corte or date.today()

        posicion = self._posicion.obtener(
            persona_id,
            fecha_corte=corte,
        )
        planificacion = self._planificacion.obtener(
            persona_id,
            fecha_corte=corte,
            horizonte_meses=horizonte_meses,
        )
        escenarios = self._escenarios.obtener(
            persona_id,
            fecha_corte=corte,
            horizonte_meses=horizonte_meses,
        )
        rendimiento = self._rendimiento.obtener(
            persona_id,
            fecha_corte=corte,
            inflacion_mensual_supuesto=inflacion_mensual_supuesta,
        )

        return ReporteFinancieroPersona(
            persona_id=persona_id,
            nombre_persona=f"{persona.nombre} {persona.apellido}".strip(),
            fecha_corte=corte,
            inflacion_mensual_supuesta=inflacion_mensual_supuesta,
            horizonte_meses=horizonte_meses,
            posicion=posicion,
            planificacion=planificacion,
            escenarios=escenarios,
            rendimiento=rendimiento,
        )


class ServicioReporteFinancieroPersona:
    """Caso de uso de lectura para la pantalla de reportes."""

    def __init__(self, db: BaseDatos) -> None:
        self._query = ReporteFinancieroPersonaQuery(db)

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        inflacion_mensual_supuesta: Decimal = Decimal("0.05"),
        horizonte_meses: int = 12,
    ) -> ReporteFinancieroPersona:
        return self._query.obtener(
            persona_id,
            fecha_corte=fecha_corte,
            inflacion_mensual_supuesta=inflacion_mensual_supuesta,
            horizonte_meses=horizonte_meses,
        )
