"""Reglas compartidas para aplicar pagos.

Este modulo define una politica declarativa para que las distintas rutas
del sistema usen el mismo criterio de asignacion.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .excepciones import ErrorValidacion
from .tipos import ConceptoImputacion, ConvencionDias, rate


class EstrategiaObligacionesPago(str, Enum):
    VENCIDA_MAS_ANTIGUA = "VENCIDA_MAS_ANTIGUA"


class BaseMoraPago(str, Enum):
    CUOTA_CONTRACTUAL = "CUOTA_CONTRACTUAL"
    CAPITAL_VENCIDO = "CAPITAL_VENCIDO"


ORDEN_WATERFALL_CANONICO = (
    ConceptoImputacion.MORA,
    ConceptoImputacion.INTERES,
    ConceptoImputacion.CAPITAL,
)
ORDEN_WATERFALL_SOPORTADO = frozenset(ORDEN_WATERFALL_CANONICO)


@dataclass(frozen=True)
class PoliticaImputacionPago:
    estrategia_obligaciones: EstrategiaObligacionesPago = EstrategiaObligacionesPago.VENCIDA_MAS_ANTIGUA
    orden_waterfall: tuple[ConceptoImputacion, ...] = ORDEN_WATERFALL_CANONICO
    interes_compensatorio_post_vencimiento: bool = True
    mora_habilitada: bool = True
    mora_tasa_anual: str = "0.50"
    mora_base: BaseMoraPago = BaseMoraPago.CUOTA_CONTRACTUAL
    mora_convencion_dias: ConvencionDias = ConvencionDias.ACTUAL_365
    capitalizacion_intereses: bool = False

    def __post_init__(self) -> None:
        orden = tuple(self.orden_waterfall)
        if not orden or len(set(orden)) != len(orden):
            raise ErrorValidacion("El waterfall no puede estar vacio ni repetir conceptos")
        if any(not isinstance(c, ConceptoImputacion) for c in orden):
            raise ErrorValidacion("El waterfall contiene conceptos invalidos")
        if any(c not in ORDEN_WATERFALL_SOPORTADO for c in orden):
            raise ErrorValidacion(
                "El waterfall incluye conceptos que la ruta de pagos todavía no soporta"
            )
        if set(orden) != ORDEN_WATERFALL_SOPORTADO:
            raise ErrorValidacion(
                "El waterfall debe contener MORA, INTERES y CAPITAL exactamente una vez"
            )
        if self.estrategia_obligaciones is not EstrategiaObligacionesPago.VENCIDA_MAS_ANTIGUA:
            raise ErrorValidacion("Estrategia de obligaciones no soportada")
        object.__setattr__(self, "orden_waterfall", orden)
        object.__setattr__(self, "mora_tasa_anual", rate(self.mora_tasa_anual))
        if self.mora_convencion_dias is not ConvencionDias.ACTUAL_365:
            raise ErrorValidacion("La convencion actual de mora requiere ACTUAL_365")
        if self.capitalizacion_intereses:
            raise ErrorValidacion("La capitalizacion de intereses no esta habilitada")

    @classmethod
    def canonica(cls) -> "PoliticaImputacionPago":
        return cls()
