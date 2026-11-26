"""Read model de cobros futuros por fecha para una persona inversora.

Reutiliza los flujos proyectados del análisis financiero existente. No calcula
cuotas, no consulta SQLite directamente y no convierte una proyección en un
hecho real. Los escenarios solo desplazan la fecha esperada o excluyen el cobro
durante el horizonte configurado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum

from aplicacion.consultas.analisis_financiero import (
    AnalisisFinancieroQuery,
    FlujoCajaFinanciero,
)
from aplicacion.puertos.persona_financiera import ConsultaExistenciaPersonaFinanciera
from dominio.tipos import money

ZERO = Decimal("0.00")
HORIZONTE_PREDETERMINADO_DIAS = 365
MAX_HORIZONTE_DIAS = 1095
MAX_DEMORA_DIAS = 365


class EstadoCobroEnEscenario(str, Enum):
    """Tratamiento de cada cobro dentro del escenario seleccionado."""

    EN_HORIZONTE = "EN_HORIZONTE"
    FUERA_DEL_HORIZONTE = "FUERA_DEL_HORIZONTE"
    NO_RECIBIDO = "NO_RECIBIDO"


@dataclass(frozen=True)
class CobroFuturoFechado:
    """Cobro contractual proyectado y su tratamiento en un escenario."""

    fecha_prevista: date
    fecha_escenario: date | None
    monto_ars: Decimal
    prestamo_id: int
    prestamo_numero: str
    tipo: str
    origen: str
    estado_escenario: EstadoCobroEnEscenario


@dataclass(frozen=True)
class ProyeccionCobrosFuturosPersona:
    """Cobros proyectados de una persona dentro de un horizonte fechado."""

    persona_id: int
    fecha_corte: date
    fecha_fin: date
    horizonte_dias: int
    demora_dias: int | None
    cobros: tuple[CobroFuturoFechado, ...]
    total_previsto_ars: Decimal
    total_en_escenario_ars: Decimal
    total_fuera_del_horizonte_ars: Decimal
    total_no_recibido_ars: Decimal

    @property
    def cantidad_cobros(self) -> int:
        return len(self.cobros)

    @property
    def cantidad_en_escenario(self) -> int:
        return sum(
            1
            for cobro in self.cobros
            if cobro.estado_escenario is EstadoCobroEnEscenario.EN_HORIZONTE
        )


class CobrosFuturosPersonaQuery:
    """Proyecta cobros de inversiones propias respetando la fecha de cada flujo."""

    def __init__(
        self,
        *,
        personas: ConsultaExistenciaPersonaFinanciera,
        analisis: AnalisisFinancieroQuery,
    ) -> None:
        self._personas = personas
        self._analisis = analisis

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        horizonte_dias: int = HORIZONTE_PREDETERMINADO_DIAS,
        demora_dias: int | None = 0,
    ) -> ProyeccionCobrosFuturosPersona:
        """Devuelve cobros futuros del rol inversor, sin alterar flujos originales.

        `demora_dias=0` usa la fecha contractual proyectada.
        `demora_dias=30|60` desplaza cada cobro esa cantidad de días.
        `demora_dias=None` simula que no se recibe ninguno en el horizonte.

        Las proyecciones se muestran únicamente como contexto. No se suman a un
        margen mensual declarado, porque la persona pudo haberlas incluido ya.
        """

        if persona_id <= 0:
            raise ValueError("persona_id debe ser positivo")
        if (
            isinstance(horizonte_dias, bool)
            or not isinstance(horizonte_dias, int)
            or not 1 <= horizonte_dias <= MAX_HORIZONTE_DIAS
        ):
            raise ValueError(
                f"horizonte_dias debe estar entre 1 y {MAX_HORIZONTE_DIAS}"
            )
        if demora_dias is not None and (
            isinstance(demora_dias, bool)
            or not isinstance(demora_dias, int)
            or not 0 <= demora_dias <= MAX_DEMORA_DIAS
        ):
            raise ValueError(
                f"demora_dias debe estar entre 0 y {MAX_DEMORA_DIAS}, o ser None"
            )

        if not self._personas.existe(persona_id):
            raise ValueError(f"La persona {persona_id} no existe")

        corte = fecha_corte or date.today()
        fin = corte + timedelta(days=horizonte_dias)
        analisis = self._analisis.obtener(persona_id, fecha_corte=corte)

        flujos = sorted(
            (
                flujo
                for flujo in analisis.flujos_proyectados
                if _es_cobro_futuro_de_inversion(flujo, corte, fin)
            ),
            key=lambda flujo: (
                flujo.fecha,
                flujo.prestamo_numero,
                flujo.prestamo_id,
                flujo.tipo,
            ),
        )

        cobros: list[CobroFuturoFechado] = []
        total_previsto = ZERO
        total_en_escenario = ZERO
        total_fuera = ZERO
        total_no_recibido = ZERO

        for flujo in flujos:
            monto = money(flujo.monto_ars)
            total_previsto += monto

            if demora_dias is None:
                fecha_escenario = None
                estado = EstadoCobroEnEscenario.NO_RECIBIDO
                total_no_recibido += monto
            else:
                fecha_escenario = flujo.fecha + timedelta(days=demora_dias)
                if fecha_escenario <= fin:
                    estado = EstadoCobroEnEscenario.EN_HORIZONTE
                    total_en_escenario += monto
                else:
                    estado = EstadoCobroEnEscenario.FUERA_DEL_HORIZONTE
                    total_fuera += monto

            cobros.append(
                CobroFuturoFechado(
                    fecha_prevista=flujo.fecha,
                    fecha_escenario=fecha_escenario,
                    monto_ars=monto,
                    prestamo_id=flujo.prestamo_id,
                    prestamo_numero=flujo.prestamo_numero,
                    tipo=flujo.tipo,
                    origen=flujo.origen,
                    estado_escenario=estado,
                )
            )

        return ProyeccionCobrosFuturosPersona(
            persona_id=persona_id,
            fecha_corte=corte,
            fecha_fin=fin,
            horizonte_dias=horizonte_dias,
            demora_dias=demora_dias,
            cobros=tuple(cobros),
            total_previsto_ars=money(total_previsto),
            total_en_escenario_ars=money(total_en_escenario),
            total_fuera_del_horizonte_ars=money(total_fuera),
            total_no_recibido_ars=money(total_no_recibido),
        )


class ServicioCobrosFuturosPersona:
    """Caso de uso de lectura de cobros futuros fechados."""

    def __init__(self, consulta: CobrosFuturosPersonaQuery) -> None:
        self._consulta = consulta

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        horizonte_dias: int = HORIZONTE_PREDETERMINADO_DIAS,
        demora_dias: int | None = 0,
    ) -> ProyeccionCobrosFuturosPersona:
        return self._consulta.obtener(
            persona_id,
            fecha_corte=fecha_corte,
            horizonte_dias=horizonte_dias,
            demora_dias=demora_dias,
        )


def _es_cobro_futuro_de_inversion(
    flujo: FlujoCajaFinanciero,
    corte: date,
    fin: date,
) -> bool:
    """Solo admite entradas futuras proyectadas del rol inversor."""

    return (
        flujo.real is False
        and flujo.rol == "inversor"
        and flujo.monto_ars > ZERO
        and corte < flujo.fecha <= fin
    )


__all__ = [
    "EstadoCobroEnEscenario",
    "CobroFuturoFechado",
    "ProyeccionCobrosFuturosPersona",
    "CobrosFuturosPersonaQuery",
    "ServicioCobrosFuturosPersona",
]
