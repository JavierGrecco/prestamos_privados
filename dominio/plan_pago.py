"""Plan puro para decidir cómo se aplica un pago a un crédito.

Acá vive la parte que antes estaba repartida entre la simulación y
``ServicioPagos``. La función no sabe nada de SQLite: recibe las cuotas tal
como están en ese momento y devuelve un plan que después puede mostrarse o
persistirse.
"""
from dataclasses import dataclass
from decimal import Decimal

from .escenarios_pago import DeudaPago, ResultadoPago, simular_pago
from .tipos import money
from .excepciones import ErrorValidacion


@dataclass(frozen=True)
class CuotaParaPago:
    """Estado mínimo de una cuota necesario para armar el plan."""

    id: int
    numero: int
    estado: str
    interes_pendiente: Decimal
    capital_pendiente: Decimal
    mora_pendiente: Decimal
    fue_mora: bool
    tuvo_pago_parcial: bool
    fue_recalculada: bool

    def __post_init__(self) -> None:
        for nombre in (
            "interes_pendiente",
            "capital_pendiente",
            "mora_pendiente",
        ):
            valor = money(getattr(self, nombre))
            if valor < 0:
                raise ErrorValidacion(f"La cuota no puede tener {nombre} negativo")
            object.__setattr__(self, nombre, valor)


@dataclass(frozen=True)
class ActualizacionCuotaPago:
    """Cambios que debería recibir una cuota al confirmar el plan."""

    cuota_id: int
    estado: str
    interes_pendiente: Decimal
    capital_pendiente: Decimal
    mora_pendiente: Decimal
    fue_mora: bool
    tuvo_pago_parcial: bool
    fue_recalculada: bool


@dataclass(frozen=True)
class PlanPago:
    """Resultado completo de una decisión de pago, sin modificar datos."""

    resultado: ResultadoPago
    monto_a_capital: Decimal
    interes_extra_generado_por_pago: Decimal
    actualizaciones: tuple[ActualizacionCuotaPago, ...]


def planificar_pago(
    monto: Decimal,
    cuotas: list[CuotaParaPago],
    cuota_objetivo_id: int,
    cuota_interes: Decimal,
    cuota_capital: Decimal,
    tasa_mensual: Decimal,
    arrastre_interes: Decimal,
    arrastre_capital: Decimal,
    arrastre_mora: Decimal,
    interes_extra: Decimal,
    mora_nueva: Decimal,
) -> PlanPago:
    """Construye el mismo plan que después debe aplicar el registro real."""
    objetivo_idx = next(
        (i for i, cuota in enumerate(cuotas) if cuota.id == cuota_objetivo_id),
        None,
    )
    if objetivo_idx is None:
        raise ErrorValidacion("No se encontró la cuota objetivo")

    deuda = DeudaPago(
        cuota_interes=cuota_interes,
        cuota_capital=cuota_capital,
        arrastre_interes=arrastre_interes,
        arrastre_capital=arrastre_capital,
        arrastre_mora=arrastre_mora,
        interes_extra=interes_extra,
        mora_nueva=mora_nueva,
    )
    resultado = simular_pago(
        monto=monto,
        deuda=deuda,
        tasa_mensual=tasa_mensual,
    )

    # Primero agotamos lo que ya estaba vencido. Recién después tocamos la
    # cuota objetivo. Esto conserva el waterfall que usa el sistema actual.
    restante_mora = resultado.aplicado_mora
    restante_interes = resultado.aplicado_interes
    restante_capital = resultado.aplicado_capital

    actualizaciones: list[ActualizacionCuotaPago] = []
    for cuota in cuotas[:objetivo_idx]:
        if cuota.estado not in ("PENDIENTE", "PARCIAL"):
            continue
        if (
            cuota.mora_pendiente == 0
            and cuota.interes_pendiente == 0
            and cuota.capital_pendiente == 0
        ):
            continue

        nueva_mora = cuota.mora_pendiente
        nuevo_interes = cuota.interes_pendiente
        nuevo_capital = cuota.capital_pendiente

        if restante_mora > 0:
            aplicado = min(restante_mora, nueva_mora)
            nueva_mora = money(nueva_mora - aplicado)
            restante_mora = money(restante_mora - aplicado)

        if restante_interes > 0:
            aplicado = min(restante_interes, nuevo_interes)
            nuevo_interes = money(nuevo_interes - aplicado)
            restante_interes = money(restante_interes - aplicado)

        if restante_capital > 0:
            aplicado = min(restante_capital, nuevo_capital)
            nuevo_capital = money(nuevo_capital - aplicado)
            restante_capital = money(restante_capital - aplicado)

        pendiente = any(
            valor > 0 for valor in (nueva_mora, nuevo_interes, nuevo_capital)
        )
        estado = "PARCIAL" if pendiente else "PAGADA"
        actualizaciones.append(
            ActualizacionCuotaPago(
                cuota_id=cuota.id,
                estado=estado,
                interes_pendiente=nuevo_interes,
                capital_pendiente=nuevo_capital,
                mora_pendiente=nueva_mora,
                fue_mora=cuota.fue_mora,
                tuvo_pago_parcial=cuota.tuvo_pago_parcial or pendiente,
                fue_recalculada=cuota.fue_recalculada,
            )
        )

    objetivo = cuotas[objetivo_idx]
    nueva_mora_obj = mora_nueva
    if restante_mora > 0:
        aplicado = min(restante_mora, nueva_mora_obj)
        nueva_mora_obj = money(nueva_mora_obj - aplicado)
        restante_mora = money(restante_mora - aplicado)

    interes_obj_total = money(cuota_interes + interes_extra)
    pago_interes_obj = min(restante_interes, interes_obj_total)
    nuevo_interes_obj = money(interes_obj_total - pago_interes_obj)

    pago_capital_obj = min(restante_capital, cuota_capital)
    nuevo_capital_obj = money(cuota_capital - pago_capital_obj)

    pendiente_obj = any(
        valor > 0 for valor in (nueva_mora_obj, nuevo_interes_obj, nuevo_capital_obj)
    )
    estado_obj = "PARCIAL" if pendiente_obj else "PAGADA"

    actualizaciones.append(
        ActualizacionCuotaPago(
            cuota_id=objetivo.id,
            estado=estado_obj,
            interes_pendiente=nuevo_interes_obj,
            capital_pendiente=nuevo_capital_obj,
            mora_pendiente=nueva_mora_obj,
            fue_mora=objetivo.fue_mora or mora_nueva > 0,
            tuvo_pago_parcial=objetivo.tuvo_pago_parcial or pendiente_obj,
            fue_recalculada=objetivo.fue_recalculada,
        )
    )

    # Este campo histórico representa el costo nuevo causado por la decisión
    # sobre la cuota corriente, no todo el interés proyectado del período.
    interes_extra_generado_por_pago = resultado.interes_extra_generado_por_pago

    return PlanPago(
        resultado=resultado,
        monto_a_capital=resultado.excedente,
        interes_extra_generado_por_pago=interes_extra_generado_por_pago,
        actualizaciones=tuple(actualizaciones),
    )
