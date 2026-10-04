"""
Estrategias de rendimiento editables.

Una estrategia describe cómo evoluciona la tasa de interés a lo
largo de un préstamo, con qué objetivos y con qué límites.

El caso típico en Argentina: un préstamo a tasa fija se licúa con
la inflación. Para compensar, se puede diseñar una estrategia que
suba la tasa año a año (step-up) o que combine tasa fija con
indexación parcial.

El usuario puede usar estrategias predefinidas, clonarlas y
editarlas, o crear las suyas desde cero.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from .tipos import ModalidadTasa, rate, money


class TipoAjuste(str, Enum):
    """Cómo evoluciona la tasa a lo largo del préstamo."""
    FIJO = "FIJO"
    STEP_UP = "STEP_UP"                      # Sube en escalones
    INDEXADO_PARCIAL = "INDEXADO_PARCIAL"    # Parte sigue la inflación
    HIBRIDO = "HIBRIDO"                      # Step-up + indexación
    ESCALONADO_INVERSO = "ESCALONADO_INVERSO"  # Arranca alto y baja


@dataclass
class AjusteProgramado:
    """Un cambio de tasa programado."""
    mes_inicio: int
    nueva_tasa: Decimal
    motivo: str = ""


@dataclass
class EstrategiaRendimiento:
    """Una estrategia de rendimiento completa."""
    nombre: str
    descripcion: str
    tipo: TipoAjuste
    tasa_base: Decimal
    modalidad: ModalidadTasa = ModalidadTasa.TNA
    ajustes_programados: list[AjusteProgramado] = field(default_factory=list)
    porcentaje_indexado: Decimal = Decimal("0")
    indice_referencia: str = "IPC"
    tasa_real_minima: Decimal = Decimal("0.05")
    licuacion_maxima_aceptable: Decimal = Decimal("0.30")


def calcular_tasa_efectiva_estrategia(
    estrategia: EstrategiaRendimiento,
    meses: int,
) -> Decimal:
    """
    Calcula la tasa efectiva promedio ponderada de una estrategia.

    Ejemplo:
        Estrategia 25% (12m) → 30% (12m) → 35% (12m):
        Tasa efectiva = (25*12 + 30*12 + 35*12) / 36 = 30%
    """
    if estrategia.tipo == TipoAjuste.FIJO or not estrategia.ajustes_programados:
        return estrategia.tasa_base

    tramos = []
    mes_actual = 1
    tasa_actual = estrategia.tasa_base

    for ajuste in sorted(estrategia.ajustes_programados, key=lambda a: a.mes_inicio):
        if ajuste.mes_inicio > mes_actual:
            tramos.append((tasa_actual, ajuste.mes_inicio - mes_actual))
        tasa_actual = ajuste.nueva_tasa
        mes_actual = ajuste.mes_inicio

    if mes_actual <= meses:
        tramos.append((tasa_actual, meses - mes_actual + 1))

    suma_ponderada = sum(tasa * meses_tramo for tasa, meses_tramo in tramos)
    return rate(suma_ponderada / Decimal(meses))


def estrategias_predefinidas_argentina() -> list[EstrategiaRendimiento]:
    """
    Cuatro estrategias típicas para el contexto argentino.
    El usuario puede usarlas tal cual, clonarlas y editarlas.
    """
    return [
        EstrategiaRendimiento(
            nombre="Escalona Simple",
            descripcion=(
                "Empieza con tasa moderada y la sube cada año para "
                "compensar la licuación. Previsible para el deudor."
            ),
            tipo=TipoAjuste.STEP_UP,
            tasa_base=Decimal("0.25"),
            ajustes_programados=[
                AjusteProgramado(12, Decimal("0.30"), "Ajuste año 2"),
                AjusteProgramado(24, Decimal("0.35"), "Ajuste año 3"),
            ],
            tasa_real_minima=Decimal("0.05"),
        ),
        EstrategiaRendimiento(
            nombre="Indexada Parcial",
            descripcion=(
                "Combina tasa fija con un componente que sigue la "
                "inflación. Protege sin ajustes manuales."
            ),
            tipo=TipoAjuste.INDEXADO_PARCIAL,
            tasa_base=Decimal("0.15"),
            porcentaje_indexado=Decimal("0.50"),
            tasa_real_minima=Decimal("0.03"),
        ),
        EstrategiaRendimiento(
            nombre="Híbrida Conservadora",
            descripcion=(
                "Step-up con indexación parcial. Para préstamos largos "
                "donde se busca equilibrio."
            ),
            tipo=TipoAjuste.HIBRIDO,
            tasa_base=Decimal("0.20"),
            ajustes_programados=[
                AjusteProgramado(18, Decimal("0.25"), "Ajuste a 18 meses"),
                AjusteProgramado(36, Decimal("0.28"), "Ajuste a 36 meses"),
            ],
            porcentaje_indexado=Decimal("0.30"),
            tasa_real_minima=Decimal("0.04"),
            licuacion_maxima_aceptable=Decimal("0.25"),
        ),
        EstrategiaRendimiento(
            nombre="Agresiva Anti-Licuación",
            descripcion=(
                "Arranca alta para compensar licuación esperada. "
                "Apropiada si se proyecta inflación alta."
            ),
            tipo=TipoAjuste.ESCALONADO_INVERSO,
            tasa_base=Decimal("0.38"),
            ajustes_programados=[
                AjusteProgramado(12, Decimal("0.32"), "Reduce año 2"),
                AjusteProgramado(24, Decimal("0.28"), "Reduce año 3"),
            ],
            tasa_real_minima=Decimal("0.08"),
        ),
    ]