"""Evaluación directa y explicable de una cuota con margen libre declarado.

El margen ya debe incluir gastos y obligaciones actuales. Esta consulta pura
solo descuenta la cuota nueva y el colchón opcional; no accede a personas,
repositorios, sesiones ni SQLite.

El respaldo de liquidez se mantiene separado del margen mensual. Solo se
considera utilizable la reserva líquida que la persona declara disponible y
que no ha decidido proteger.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum

from dominio.tipos import money


class EstadoCobroFuturo(str, Enum):
    """Estado de un cobro externo declarado por la persona."""

    PENDIENTE = "PENDIENTE"
    COBRADO = "COBRADO"
    CANCELADO = "CANCELADO"


class FuenteCobroFuturo(str, Enum):
    """Procedencia del dato que alimenta la proyección de caja."""

    EXTERNO_DECLARADO = "EXTERNO_DECLARADO"
    SISTEMA_CONTRACTUAL = "SISTEMA_CONTRACTUAL"


@dataclass(frozen=True)
class CobroFuturoDeclarado:
    """Flujo futuro externo o proveniente del read model contractual."""

    importe: Decimal | int | float | str
    fecha_prevista: date
    origen: str
    estado: EstadoCobroFuturo | str = EstadoCobroFuturo.PENDIENTE
    incluido_en_margen: bool = False
    fuente: FuenteCobroFuturo | str = FuenteCobroFuturo.EXTERNO_DECLARADO
    referencia: str | None = None


@dataclass(frozen=True)
class PeriodoRespaldoConCobros:
    """Resultado de caja disponible al llegar a cada vencimiento mensual."""

    numero_mes: int
    fecha_vencimiento: date
    cobros_esperados_hasta_vencimiento: Decimal
    cobros_sistema_hasta_vencimiento: Decimal
    cobros_externos_hasta_vencimiento: Decimal
    faltante_del_mes: Decimal
    faltante_no_cubierto: Decimal


@dataclass(frozen=True)
class EvaluacionRespaldoTemporal:
    """Proyección temporal que incorpora cobros solo desde su fecha efectiva."""

    demora_cobros_dias: int | None
    respaldo_utilizable_inicial: Decimal
    total_cobros_en_escenario: Decimal
    total_cobros_sistema_en_escenario: Decimal
    total_cobros_externos_en_escenario: Decimal
    total_cobros_fuera_horizonte: Decimal
    total_cobros_vencidos_no_recibidos: Decimal
    total_cobros_no_recibidos_escenario: Decimal
    total_cobros_ya_recibidos_excluidos: Decimal
    total_cobros_cancelados_excluidos: Decimal
    total_cobros_incluidos_en_margen_excluidos: Decimal
    faltante_mensual_escenario: Decimal
    faltante_no_cubierto_total: Decimal
    saldo_respaldo_final: Decimal
    meses_con_faltante: int
    periodos: tuple[PeriodoRespaldoConCobros, ...]


ZERO = Decimal("0.00")
CENT = Decimal("0.01")
MAX_MESES_ESCENARIO = 24
MAX_COBROS_ESCENARIO = 5000


@dataclass(frozen=True)
class EvaluacionRespaldoLiquidez:
    """Resultado del escenario de caja cubierto con una reserva líquida."""

    reserva_liquida_declarada: Decimal
    reserva_minima_protegida: Decimal
    reserva_utilizable: Decimal
    margen_libre_mes_ajustado: Decimal | None
    remanente_mes_ajustado: Decimal | None
    meses_escenario_ajustado: int | None
    faltante_mensual_escenario: Decimal | None
    respaldo_requerido_escenario: Decimal | None
    meses_completos_cubiertos: int | None
    respaldo_consumido_escenario: Decimal | None
    respaldo_restante_escenario: Decimal | None
    faltante_no_cubierto_escenario: Decimal | None
    proyeccion_temporal: EvaluacionRespaldoTemporal | None = None


@dataclass(frozen=True)
class EvaluacionCapacidadPagoDirecta:
    """Resultado de comparar una cuota nueva con dinero libre declarado."""

    margen_libre_declarado: Decimal
    cuota_nueva_mensual: Decimal
    colchon_mensual: Decimal
    remanente_mensual: Decimal
    porcentaje_margen_comprometido: Decimal | None
    respaldo_liquidez: EvaluacionRespaldoLiquidez


def _normalizar_importe(
    valor: Decimal | int | float | str,
    nombre: str,
) -> Decimal:
    try:
        importe = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{nombre} debe ser un importe válido") from exc

    if not importe.is_finite():
        raise ValueError(f"{nombre} debe ser un importe finito")

    return money(importe)



def _sumar_meses(fecha_base: date, meses: int) -> date:
    """Suma meses calendario y limita el día al último día del mes destino."""

    indice = fecha_base.year * 12 + fecha_base.month - 1 + meses
    anio, mes_cero = divmod(indice, 12)
    mes = mes_cero + 1
    dia = min(fecha_base.day, monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def evaluar_respaldo_liquidez_con_cobros_futuros(
    *,
    reserva_utilizable_inicial: Decimal | int | float | str,
    faltante_mensual: Decimal | int | float | str,
    fecha_primer_vencimiento: date,
    meses: int,
    cobros: tuple[CobroFuturoDeclarado, ...] | list[CobroFuturoDeclarado],
    demora_dias: int | None = 0,
    fecha_referencia: date | None = None,
) -> EvaluacionRespaldoTemporal:
    """Simula la caja mensual sin anticipar cobros ni duplicar el margen.

    Un cobro pendiente ingresa en la fecha prevista o en la fecha demorada.
    Solo puede cubrir un vencimiento en esa fecha o uno posterior. Los cobros
    vencidos que siguen pendientes, ya recibidos, cancelados o ya incluidos en
    el margen declarado no se vuelven a sumar. La reserva protegida debe
    haberse descontado antes de llamar esta función.
    """

    reserva_inicial = _normalizar_importe(
        reserva_utilizable_inicial,
        "El respaldo utilizable inicial",
    )
    faltante = _normalizar_importe(faltante_mensual, "El faltante mensual")
    if reserva_inicial < ZERO:
        raise ValueError("El respaldo utilizable inicial no puede ser negativo")
    if faltante < ZERO:
        raise ValueError("El faltante mensual no puede ser negativo")
    if (
        isinstance(meses, bool)
        or not isinstance(meses, int)
        or not 1 <= meses <= MAX_MESES_ESCENARIO
    ):
        raise ValueError(
            f"La duración del escenario debe estar entre 1 y {MAX_MESES_ESCENARIO} meses"
        )
    if (
        isinstance(demora_dias, bool)
        or (demora_dias is not None and demora_dias not in (0, 30, 60))
    ):
        raise ValueError("La demora debe ser 0, 30, 60 días o ausencia de cobro")
    if not isinstance(fecha_primer_vencimiento, date):
        raise ValueError("La fecha del primer vencimiento no es válida")

    referencia = fecha_referencia or date.today()
    if not isinstance(referencia, date):
        raise ValueError("La fecha de referencia no es válida")
    if fecha_primer_vencimiento < referencia:
        raise ValueError(
            "El primer vencimiento no puede ser anterior a la fecha de referencia"
        )
    if len(cobros) > MAX_COBROS_ESCENARIO:
        raise ValueError(
            f"Se pueden analizar hasta {MAX_COBROS_ESCENARIO} cobros por escenario"
        )

    ultimo_vencimiento = _sumar_meses(fecha_primer_vencimiento, meses - 1)
    agenda: list[tuple[date, Decimal, FuenteCobroFuturo]] = []
    referencias_vistas: set[str] = set()
    total_fuera_horizonte = ZERO
    total_vencidos = ZERO
    total_no_recibidos = ZERO
    total_ya_recibidos = ZERO
    total_cancelados = ZERO
    total_incluidos_en_margen = ZERO

    for cobro in cobros:
        if not isinstance(cobro, CobroFuturoDeclarado):
            raise ValueError("Cada cobro futuro debe tener un registro válido")
        importe = _normalizar_importe(cobro.importe, "El importe del cobro futuro")
        if importe <= ZERO:
            raise ValueError("El importe del cobro futuro debe ser mayor que cero")
        if not isinstance(cobro.fecha_prevista, date):
            raise ValueError("La fecha prevista del cobro no es válida")
        if not isinstance(cobro.origen, str) or not cobro.origen.strip():
            raise ValueError("El origen del cobro futuro es obligatorio")
        if not isinstance(cobro.incluido_en_margen, bool):
            raise ValueError("La marca de inclusión en el margen debe ser booleana")

        try:
            estado = EstadoCobroFuturo(cobro.estado)
            fuente = FuenteCobroFuturo(cobro.fuente)
        except (TypeError, ValueError) as exc:
            raise ValueError("El estado o la fuente del cobro futuro no es válido") from exc

        if fuente is FuenteCobroFuturo.SISTEMA_CONTRACTUAL:
            if not isinstance(cobro.referencia, str) or not cobro.referencia.strip():
                raise ValueError(
                    "Los cobros contractuales del sistema requieren una referencia"
                )
            referencia_flujo = cobro.referencia.strip()
            if referencia_flujo in referencias_vistas:
                raise ValueError(
                    "La misma referencia de cobro contractual no puede repetirse"
                )
            referencias_vistas.add(referencia_flujo)

        if estado is EstadoCobroFuturo.COBRADO:
            total_ya_recibidos += importe
            continue
        if estado is EstadoCobroFuturo.CANCELADO:
            total_cancelados += importe
            continue
        if cobro.incluido_en_margen:
            total_incluidos_en_margen += importe
            continue

        fecha_escenario = (
            None
            if demora_dias is None
            else cobro.fecha_prevista + timedelta(days=demora_dias)
        )

        if fecha_escenario is None:
            if cobro.fecha_prevista < referencia:
                total_vencidos += importe
            elif cobro.fecha_prevista > ultimo_vencimiento:
                total_fuera_horizonte += importe
            else:
                total_no_recibidos += importe
            continue

        if fecha_escenario < referencia:
            total_vencidos += importe
            continue
        if fecha_escenario > ultimo_vencimiento:
            total_fuera_horizonte += importe
            continue
        agenda.append((fecha_escenario, importe, fuente))

    agenda.sort(key=lambda item: (item[0], item[2].value))
    total_en_escenario = money(sum((importe for _, importe, _ in agenda), ZERO))
    total_sistema_en_escenario = money(
        sum(
            (importe for _, importe, fuente in agenda
             if fuente is FuenteCobroFuturo.SISTEMA_CONTRACTUAL),
            ZERO,
        )
    )
    total_externos_en_escenario = money(
        sum(
            (importe for _, importe, fuente in agenda
             if fuente is FuenteCobroFuturo.EXTERNO_DECLARADO),
            ZERO,
        )
    )
    saldo = reserva_inicial
    faltante_no_cubierto_total = ZERO
    meses_con_faltante = 0
    periodos: list[PeriodoRespaldoConCobros] = []
    indice_cobro = 0

    for numero_mes in range(1, meses + 1):
        vencimiento = _sumar_meses(fecha_primer_vencimiento, numero_mes - 1)
        cobros_periodo = ZERO
        cobros_sistema_periodo = ZERO
        cobros_externos_periodo = ZERO
        while (
            indice_cobro < len(agenda)
            and agenda[indice_cobro][0] <= vencimiento
        ):
            _, importe_cobro, fuente_cobro = agenda[indice_cobro]
            cobros_periodo += importe_cobro
            if fuente_cobro is FuenteCobroFuturo.SISTEMA_CONTRACTUAL:
                cobros_sistema_periodo += importe_cobro
            else:
                cobros_externos_periodo += importe_cobro
            indice_cobro += 1

        cobros_periodo = money(cobros_periodo)
        cobros_sistema_periodo = money(cobros_sistema_periodo)
        cobros_externos_periodo = money(cobros_externos_periodo)
        saldo = money(saldo + cobros_periodo)
        faltante_no_cubierto = money(max(ZERO, faltante - saldo))
        if faltante_no_cubierto > ZERO:
            meses_con_faltante += 1
        saldo = money(max(ZERO, saldo - faltante))
        faltante_no_cubierto_total += faltante_no_cubierto

        periodos.append(
            PeriodoRespaldoConCobros(
                numero_mes=numero_mes,
                fecha_vencimiento=vencimiento,
                cobros_esperados_hasta_vencimiento=cobros_periodo,
                cobros_sistema_hasta_vencimiento=cobros_sistema_periodo,
                cobros_externos_hasta_vencimiento=cobros_externos_periodo,
                faltante_del_mes=faltante,
                faltante_no_cubierto=faltante_no_cubierto,
                respaldo_al_cierre=saldo,
            )
        )

    return EvaluacionRespaldoTemporal(
        demora_cobros_dias=demora_dias,
        respaldo_utilizable_inicial=reserva_inicial,
        total_cobros_en_escenario=total_en_escenario,
        total_cobros_sistema_en_escenario=total_sistema_en_escenario,
        total_cobros_externos_en_escenario=total_externos_en_escenario,
        total_cobros_fuera_horizonte=money(total_fuera_horizonte),
        total_cobros_vencidos_no_recibidos=money(total_vencidos),
        total_cobros_no_recibidos_escenario=money(total_no_recibidos),
        total_cobros_ya_recibidos_excluidos=money(total_ya_recibidos),
        total_cobros_cancelados_excluidos=money(total_cancelados),
        total_cobros_incluidos_en_margen_excluidos=money(total_incluidos_en_margen),
        faltante_mensual_escenario=faltante,
        faltante_no_cubierto_total=money(faltante_no_cubierto_total),
        saldo_respaldo_final=money(saldo),
        meses_con_faltante=meses_con_faltante,
        periodos=tuple(periodos),
    )


def evaluar_capacidad_pago_directa(
    *,
    margen_libre_mensual: Decimal | int | float | str,
    cuota_nueva_mensual: Decimal | int | float | str,
    colchon_mensual: Decimal | int | float | str = ZERO,
    reserva_liquida_disponible: Decimal | int | float | str = ZERO,
    reserva_minima_protegida: Decimal | int | float | str = ZERO,
    margen_libre_mes_ajustado: Decimal | int | float | str | None = None,
    meses_escenario_ajustado: int = 1,
    cobros_futuros: tuple[CobroFuturoDeclarado, ...] | list[CobroFuturoDeclarado] = (),
    fecha_primer_vencimiento: date | None = None,
    demora_cobros_dias: int | None = 0,
    fecha_referencia: date | None = None,
) -> EvaluacionCapacidadPagoDirecta:
    """Compara una cuota con margen habitual y, opcionalmente, con un mes difícil.

    El margen declarado ya debe estar neto de gastos y obligaciones actuales.
    No se descuentan nuevamente pagos de préstamos existentes.

    La reserva líquida no se suma al margen mensual. Solo puede cubrir el
    faltante de un escenario ajustado, sin tocar la parte protegida por la
    persona. El escenario repite el mismo margen ajustado durante la cantidad
    de meses indicada; no es un pronóstico ni una proyección contractual.

    No calcula deuda/ingresos (DTI): el ingreso no forma parte de esta entrada.
    """

    margen = _normalizar_importe(margen_libre_mensual, "El margen libre")
    cuota = _normalizar_importe(cuota_nueva_mensual, "La cuota nueva")
    colchon = _normalizar_importe(colchon_mensual, "El colchón mensual")
    reserva = _normalizar_importe(
        reserva_liquida_disponible,
        "La reserva líquida disponible",
    )
    protegida = _normalizar_importe(
        reserva_minima_protegida,
        "La reserva mínima protegida",
    )

    if cuota <= ZERO:
        raise ValueError("La cuota nueva debe ser mayor que cero")
    if colchon < ZERO:
        raise ValueError("El colchón mensual no puede ser negativo")
    if reserva < ZERO:
        raise ValueError("La reserva líquida disponible no puede ser negativa")
    if protegida < ZERO:
        raise ValueError("La reserva mínima protegida no puede ser negativa")
    remanente = money(margen - cuota - colchon)
    porcentaje = None
    if margen > ZERO:
        porcentaje = (cuota / margen * Decimal("100")).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    reserva_utilizable = money(max(ZERO, reserva - protegida))
    margen_ajustado = None
    remanente_ajustado = None
    meses_ajustados = None
    faltante_mensual = None
    respaldo_requerido = None
    meses_completos_cubiertos = None
    respaldo_consumido = None
    respaldo_restante = None
    faltante_no_cubierto = None

    if margen_libre_mes_ajustado is not None:
        margen_ajustado = _normalizar_importe(
            margen_libre_mes_ajustado,
            "El margen libre del mes ajustado",
        )
        if (
            isinstance(meses_escenario_ajustado, bool)
            or not isinstance(meses_escenario_ajustado, int)
            or not 1 <= meses_escenario_ajustado <= MAX_MESES_ESCENARIO
        ):
            raise ValueError(
                f"La duración del escenario debe estar entre 1 y {MAX_MESES_ESCENARIO} meses"
            )

        meses_ajustados = meses_escenario_ajustado
        remanente_ajustado = money(margen_ajustado - cuota - colchon)
        faltante_mensual = money(max(ZERO, -remanente_ajustado))
        respaldo_requerido = money(faltante_mensual * meses_ajustados)
        respaldo_consumido = min(reserva_utilizable, respaldo_requerido)
        respaldo_restante = money(reserva_utilizable - respaldo_consumido)
        faltante_no_cubierto = money(respaldo_requerido - respaldo_consumido)

        if faltante_mensual == ZERO:
            meses_completos_cubiertos = meses_ajustados
        else:
            meses_completos_cubiertos = min(
                meses_ajustados,
                int(reserva_utilizable // faltante_mensual),
            )

    proyeccion_temporal = None
    if cobros_futuros:
        if margen_ajustado is None or meses_ajustados is None:
            raise ValueError(
                "Los cobros futuros requieren un escenario de margen ajustado"
            )
        if fecha_primer_vencimiento is None:
            raise ValueError("Falta la fecha del primer vencimiento del escenario")
        proyeccion_temporal = evaluar_respaldo_liquidez_con_cobros_futuros(
            reserva_utilizable_inicial=reserva_utilizable,
            faltante_mensual=faltante_mensual or ZERO,
            fecha_primer_vencimiento=fecha_primer_vencimiento,
            meses=meses_ajustados,
            cobros=cobros_futuros,
            demora_dias=demora_cobros_dias,
            fecha_referencia=fecha_referencia,
        )

    respaldo = EvaluacionRespaldoLiquidez(
        reserva_liquida_declarada=reserva,
        reserva_minima_protegida=protegida,
        reserva_utilizable=reserva_utilizable,
        margen_libre_mes_ajustado=margen_ajustado,
        remanente_mes_ajustado=remanente_ajustado,
        meses_escenario_ajustado=meses_ajustados,
        faltante_mensual_escenario=faltante_mensual,
        respaldo_requerido_escenario=respaldo_requerido,
        meses_completos_cubiertos=meses_completos_cubiertos,
        respaldo_consumido_escenario=respaldo_consumido,
        respaldo_restante_escenario=respaldo_restante,
        faltante_no_cubierto_escenario=faltante_no_cubierto,
        proyeccion_temporal=proyeccion_temporal,
    )

    return EvaluacionCapacidadPagoDirecta(
        margen_libre_declarado=margen,
        cuota_nueva_mensual=cuota,
        colchon_mensual=colchon,
        remanente_mensual=remanente,
        porcentaje_margen_comprometido=porcentaje,
        respaldo_liquidez=respaldo,
    )
