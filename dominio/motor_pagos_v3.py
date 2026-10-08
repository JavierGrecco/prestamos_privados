"""Motor puro de pagos V3-A.

Este módulo no conoce SQLite, Streamlit ni repositorios. Recibe snapshots
inmutables y devuelve un PlanPago determinista. La persistencia se integra en
una fase posterior.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Iterable, Mapping, Sequence

from .excepciones import ErrorInvariante, ErrorValidacion
from .tipos import ConceptoImputacion, ConvencionDias, ModalidadTasa, ORDEN_DEFAULT_IMPUTACION, money, rate

ZERO = Decimal("0.00")


class OrigenImputacion(str, Enum):
    """Origen económico de una aplicación, no su concepto contable."""

    SALDO_CONTRACTUAL = "SALDO_CONTRACTUAL"
    DEVENGAMIENTO = "DEVENGAMIENTO"
    PREPAGO = "PREPAGO"
    MIXTA = "MIXTA"


class TratamientoExcedente(str, Enum):
    """Decisión posterior al waterfall sobre dinero no imputado."""

    SALDO_A_FAVOR = "SALDO_A_FAVOR"
    PREPAGO_RAI = "PREPAGO_RAI"
    PREPAGO_RNI = "PREPAGO_RNI"


class TipoPlanPago(str, Enum):
    PARCIAL = "PARCIAL"
    COMPLEMENTO = "COMPLEMENTO"
    CUOTA = "CUOTA"
    ADELANTO = "ADELANTO"


# Política vertical por defecto de este proyecto. GASTO/PENALIZACION siguen
# disponibles en ConceptoImputacion para una política contractual futura.
ORDEN_WATERFALL_V3: tuple[ConceptoImputacion, ...] = tuple(ORDEN_DEFAULT_IMPUTACION[2:])


@dataclass(frozen=True)
class Devengamiento:
    """Monto nacido por el paso del tiempo u otra regla financiera explícita."""

    concepto: ConceptoImputacion
    monto: Decimal
    fecha_desde: date
    fecha_hasta: date
    origen: str
    referencia: str | None = None
    base: Decimal = ZERO
    tasa_anual: Decimal = ZERO
    modalidad_tasa: ModalidadTasa | None = None
    convencion_dias: ConvencionDias | None = None
    dias: int = 0
    fraccion_anual: Decimal = ZERO

    def __post_init__(self) -> None:
        monto = money(self.monto)
        base = money(self.base)
        tasa = rate(self.tasa_anual) if self.tasa_anual is not None else ZERO
        if monto < ZERO:
            raise ErrorValidacion("Un devengamiento no puede ser negativo")
        if base < ZERO:
            raise ErrorValidacion("La base del devengamiento no puede ser negativa")
        if tasa < ZERO:
            raise ErrorValidacion("La tasa del devengamiento no puede ser negativa")
        if self.fecha_hasta < self.fecha_desde:
            raise ErrorValidacion("El período del devengamiento es inválido")
        if self.dias < 0:
            raise ErrorValidacion("Los días del devengamiento no pueden ser negativos")
        if self.fraccion_anual < ZERO:
            raise ErrorValidacion("La fracción anual no puede ser negativa")
        if not self.origen:
            raise ErrorValidacion("El devengamiento debe indicar su origen")
        object.__setattr__(self, "monto", monto)
        object.__setattr__(self, "base", base)
        object.__setattr__(self, "tasa_anual", tasa)


@dataclass(frozen=True)
class SaldoObligacion:
    """Saldo financiero de una obligación, expresado por concepto."""

    gasto: Decimal = ZERO
    penalizacion: Decimal = ZERO
    mora: Decimal = ZERO
    interes: Decimal = ZERO
    capital: Decimal = ZERO

    def __post_init__(self) -> None:
        campos = ("gasto", "penalizacion", "mora", "interes", "capital")
        for nombre in campos:
            valor = money(getattr(self, nombre))
            if valor < ZERO:
                raise ErrorValidacion(f"El saldo {nombre} no puede ser negativo")
            object.__setattr__(self, nombre, valor)

    @property
    def total(self) -> Decimal:
        return money(self.gasto + self.penalizacion + self.mora + self.interes + self.capital)

    def para_concepto(self, concepto: ConceptoImputacion) -> Decimal:
        return {
            ConceptoImputacion.GASTO: self.gasto,
            ConceptoImputacion.PENALIZACION: self.penalizacion,
            ConceptoImputacion.MORA: self.mora,
            ConceptoImputacion.INTERES: self.interes,
            ConceptoImputacion.CAPITAL: self.capital,
        }[concepto]

    def con_cambio(
        self,
        *,
        gasto: Decimal | None = None,
        penalizacion: Decimal | None = None,
        mora: Decimal | None = None,
        interes: Decimal | None = None,
        capital: Decimal | None = None,
    ) -> "SaldoObligacion":
        return SaldoObligacion(
            gasto=self.gasto if gasto is None else gasto,
            penalizacion=self.penalizacion if penalizacion is None else penalizacion,
            mora=self.mora if mora is None else mora,
            interes=self.interes if interes is None else interes,
            capital=self.capital if capital is None else capital,
        )


@dataclass(frozen=True)
class ObligacionSnapshot:
    """Estado materializado de una obligación al inicio del cálculo.

    monto_mora_base conserva la cuota contractual sobre la que la política
    de mora puede calcular un devengamiento. No es el saldo pendiente y no
    participa del waterfall por sí mismo.
    """

    cuota_id: int
    numero_cuota: int
    vencimiento: date
    estado: str
    tuvo_pago_parcial: bool
    saldo: SaldoObligacion
    monto_mora_base: Decimal = ZERO

    def __post_init__(self) -> None:
        base = money(self.monto_mora_base)
        if base < ZERO:
            raise ErrorValidacion("La base de mora no puede ser negativa")
        object.__setattr__(self, "monto_mora_base", base)

    @classmethod
    def desde_cuota_actual(
        cls,
        *,
        cuota_id: int,
        numero_cuota: int,
        vencimiento: date,
        estado: str,
        tuvo_pago_parcial: bool,
        interes_pendiente: Decimal,
        capital_pendiente: Decimal,
        mora_pendiente: Decimal,
        monto_mora_base: Decimal = ZERO,
    ) -> "ObligacionSnapshot":
        return cls(
            cuota_id=cuota_id,
            numero_cuota=numero_cuota,
            vencimiento=vencimiento,
            estado=estado,
            tuvo_pago_parcial=tuvo_pago_parcial,
            saldo=SaldoObligacion(
                interes=interes_pendiente,
                capital=capital_pendiente,
                mora=mora_pendiente,
            ),
            monto_mora_base=monto_mora_base,
        )


@dataclass(frozen=True)
class AplicacionPago:
    """Aplicación atómica: PAGO -> CUOTA -> CONCEPTO -> MONTO."""

    cuota_id: int
    concepto: ConceptoImputacion
    monto: Decimal
    origen: OrigenImputacion
    referencias_devengamiento: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        monto = money(self.monto)
        if monto <= ZERO:
            raise ErrorValidacion("Una aplicación debe ser mayor a cero")
        referencias = tuple(r for r in self.referencias_devengamiento if r)
        if self.origen in (OrigenImputacion.DEVENGAMIENTO, OrigenImputacion.MIXTA) and not referencias:
            raise ErrorValidacion(
                "Una aplicación con origen de devengamiento debe identificarlo"
            )
        object.__setattr__(self, "referencias_devengamiento", referencias)
        object.__setattr__(self, "monto", monto)


@dataclass(frozen=True)
class ExcedentePago:
    """Dinero recibido que el waterfall no pudo asignar."""

    monto: Decimal
    tratamiento: TratamientoExcedente | None = None

    def __post_init__(self) -> None:
        monto = money(self.monto)
        if monto < ZERO:
            raise ErrorInvariante("El excedente no puede ser negativo")
        object.__setattr__(self, "monto", monto)


@dataclass(frozen=True)
class ObligacionAfectada:
    """Antes/después de una obligación y sus aplicaciones atómicas."""

    cuota_id: int
    numero_cuota: int
    vencimiento: date
    estado_anterior: str
    estado_posterior: str
    saldo_anterior: SaldoObligacion
    devengamientos: tuple[Devengamiento, ...]
    aplicaciones: tuple[AplicacionPago, ...]
    saldo_posterior: SaldoObligacion
    tuvo_pago_parcial_posterior: bool

    @property
    def aplicado_mora(self) -> Decimal:
        return _sumar_concepto(self.aplicaciones, ConceptoImputacion.MORA)

    @property
    def aplicado_interes(self) -> Decimal:
        return _sumar_concepto(self.aplicaciones, ConceptoImputacion.INTERES)

    @property
    def aplicado_capital(self) -> Decimal:
        return _sumar_concepto(self.aplicaciones, ConceptoImputacion.CAPITAL)

    @property
    def monto_aplicado(self) -> Decimal:
        return money(sum((a.monto for a in self.aplicaciones), ZERO))

    @property
    def mora_generada(self) -> Decimal:
        return _sumar_devengamiento(self.devengamientos, ConceptoImputacion.MORA)

    @property
    def interes_generado(self) -> Decimal:
        return _sumar_devengamiento(self.devengamientos, ConceptoImputacion.INTERES)

    def validar(self) -> None:
        """Valida la ecuación contable componente por componente."""
        if self.estado_anterior == "PAGADA" and any(d.monto > ZERO for d in self.devengamientos):
            raise ErrorInvariante(
                f"La cuota {self.cuota_id} figura PAGADA y recibió un devengamiento"
            )

        devengado = {
            concepto: _sumar_devengamiento(self.devengamientos, concepto)
            for concepto in ConceptoImputacion
        }
        aplicado = {
            concepto: _sumar_concepto(self.aplicaciones, concepto)
            for concepto in ConceptoImputacion
        }

        for concepto in ConceptoImputacion:
            esperado = money(
                self.saldo_anterior.para_concepto(concepto)
                + devengado[concepto]
                - aplicado[concepto]
            )
            observado = self.saldo_posterior.para_concepto(concepto)
            if esperado != observado:
                raise ErrorInvariante(
                    f"Saldo inconsistente en cuota {self.cuota_id}, {concepto.value}: "
                    f"esperado {esperado}, observado {observado}"
                )

        if self.saldo_posterior.total < ZERO:
            raise ErrorInvariante(f"La cuota {self.cuota_id} terminó con saldo negativo")

        deberia_ser_pagada = self.saldo_posterior.total == ZERO
        if deberia_ser_pagada and self.estado_posterior != "PAGADA":
            raise ErrorInvariante(
                f"La cuota {self.cuota_id} tiene saldo cero pero estado {self.estado_posterior}"
            )
        if not deberia_ser_pagada and self.estado_posterior == "PAGADA":
            raise ErrorInvariante(
                f"La cuota {self.cuota_id} conserva saldo pero figura PAGADA"
            )


@dataclass(frozen=True)
class PlanPago:
    """Resultado financiero canónico del motor V3."""

    prestamo_id: int
    fecha_valor: date
    revision_prestamo: int
    monto_pago_recibido: Decimal
    obligaciones_afectadas: tuple[ObligacionAfectada, ...]
    aplicaciones: tuple[AplicacionPago, ...]
    excedente: ExcedentePago
    tipo: TipoPlanPago

    @property
    def monto_aplicado(self) -> Decimal:
        return money(sum((a.monto for a in self.aplicaciones), ZERO))

    @property
    def monto_a_capital(self) -> Decimal:
        return _sumar_concepto(self.aplicaciones, ConceptoImputacion.CAPITAL)

    @property
    def mora_generada(self) -> Decimal:
        return money(
            sum((o.mora_generada for o in self.obligaciones_afectadas), ZERO)
        )

    @property
    def interes_generado(self) -> Decimal:
        return money(
            sum((o.interes_generado for o in self.obligaciones_afectadas), ZERO)
        )

    @property
    def aplicado_mora(self) -> Decimal:
        return _sumar_concepto(self.aplicaciones, ConceptoImputacion.MORA)

    @property
    def aplicado_interes(self) -> Decimal:
        return _sumar_concepto(self.aplicaciones, ConceptoImputacion.INTERES)

    def validar(self) -> None:
        monto = money(self.monto_pago_recibido)
        if monto <= ZERO:
            raise ErrorValidacion("El pago debe ser mayor a cero")
        if self.excedente.monto < ZERO:
            raise ErrorInvariante("El plan contiene excedente negativo")

        suma = money(self.monto_aplicado + self.excedente.monto)
        if suma != monto:
            raise ErrorInvariante(
                f"Conservación de dinero violada: aplicado+excedente={suma}, pago={monto}"
            )

        ids_afectadas = {o.cuota_id for o in self.obligaciones_afectadas}
        if any(a.cuota_id not in ids_afectadas for a in self.aplicaciones):
            raise ErrorInvariante("Existe una aplicación para una obligación no afectada")

        for obligacion in self.obligaciones_afectadas:
            obligacion.validar()
            por_obligacion = money(
                sum(
                    (a.monto for a in self.aplicaciones if a.cuota_id == obligacion.cuota_id),
                    ZERO,
                )
            )
            if por_obligacion != obligacion.monto_aplicado:
                raise ErrorInvariante(
                    f"Aplicaciones globales no concilian con cuota {obligacion.cuota_id}"
                )

        totales_por_concepto = {
            concepto: _sumar_concepto(self.aplicaciones, concepto)
            for concepto in ConceptoImputacion
        }
        suma_conceptos = money(sum(totales_por_concepto.values(), ZERO))
        if suma_conceptos != self.monto_aplicado:
            raise ErrorInvariante("La suma por conceptos no concilia con el total aplicado")


def calcular_plan_pago(
    *,
    prestamo_id: int,
    fecha_valor: date,
    revision_prestamo: int,
    monto_recibido: Decimal,
    obligaciones: Sequence[ObligacionSnapshot],
    devengamientos_por_cuota: Mapping[int, Sequence[Devengamiento]] | None = None,
    orden_waterfall: Sequence[ConceptoImputacion] = ORDEN_WATERFALL_V3,
) -> PlanPago:
    """Calcula el waterfall horizontal y vertical sin efectos secundarios.

    Las obligaciones se procesan en el orden recibido. La capa de aplicación
    debe entregarlas cronológicamente por vencimiento/numero de cuota.
    """
    monto = money(monto_recibido)
    if monto <= ZERO:
        raise ErrorValidacion("El monto recibido debe ser mayor a cero")
    if revision_prestamo < 0:
        raise ErrorValidacion("La revisión del préstamo no puede ser negativa")

    _validar_orden(orden_waterfall)
    _validar_obligaciones(obligaciones=obligaciones)

    devengamientos_por_cuota = devengamientos_por_cuota or {}
    ids_obligaciones = {o.cuota_id for o in obligaciones}
    ids_devengamientos = set(devengamientos_por_cuota)
    if not ids_devengamientos.issubset(ids_obligaciones):
        desconocidas = sorted(ids_devengamientos - ids_obligaciones)
        raise ErrorValidacion(
            f"Existen devengamientos para cuotas inexistentes: {desconocidas}"
        )
    _validar_conceptos_cobrables(obligaciones, devengamientos_por_cuota, orden_waterfall)

    remanente = monto
    afectadas: list[ObligacionAfectada] = []
    aplicaciones_globales: list[AplicacionPago] = []
    for snapshot in obligaciones:
        nuevos = tuple(devengamientos_por_cuota.get(snapshot.cuota_id, ()))
        if snapshot.saldo.total == ZERO and not nuevos:
            continue

        saldo_con_devengamientos = _agregar_devengamientos(snapshot.saldo, nuevos)
        if saldo_con_devengamientos.total == ZERO:
            continue

        aplicaciones: list[AplicacionPago] = []
        restante_obligacion = remanente

        for concepto in orden_waterfall:
            if restante_obligacion <= ZERO:
                break
            disponible = saldo_con_devengamientos.para_concepto(concepto)
            if disponible <= ZERO:
                continue

            aplicado = min(restante_obligacion, disponible)
            if aplicado <= ZERO:
                continue

            tiene_contractual = snapshot.saldo.para_concepto(concepto) > ZERO
            tiene_devengamiento = _hay_devengamiento_para_concepto(nuevos, concepto)
            if tiene_contractual and tiene_devengamiento:
                origen = OrigenImputacion.MIXTA
            elif tiene_devengamiento:
                origen = OrigenImputacion.DEVENGAMIENTO
            else:
                origen = OrigenImputacion.SALDO_CONTRACTUAL
            referencias = _referencias_para_aplicacion(nuevos, concepto)
            aplicaciones.append(
                AplicacionPago(
                    cuota_id=snapshot.cuota_id,
                    concepto=concepto,
                    monto=aplicado,
                    origen=origen,
                    referencias_devengamiento=referencias,
                )
            )
            aplicaciones_globales.append(aplicaciones[-1])
            restante_obligacion = money(restante_obligacion - aplicado)

        saldo_posterior = _restar_aplicaciones(saldo_con_devengamientos, aplicaciones)
        estado_posterior = "PAGADA" if saldo_posterior.total == ZERO else "PARCIAL"
        hubo_aplicacion = bool(aplicaciones)
        tuvo_parcial_posterior = snapshot.tuvo_pago_parcial or (
            hubo_aplicacion and estado_posterior == "PARCIAL"
        )

        afectada = ObligacionAfectada(
            cuota_id=snapshot.cuota_id,
            numero_cuota=snapshot.numero_cuota,
            vencimiento=snapshot.vencimiento,
            estado_anterior=snapshot.estado,
            estado_posterior=estado_posterior,
            saldo_anterior=snapshot.saldo,
            devengamientos=nuevos,
            aplicaciones=tuple(aplicaciones),
            saldo_posterior=saldo_posterior,
            tuvo_pago_parcial_posterior=tuvo_parcial_posterior,
        )
        afectada.validar()
        afectadas.append(afectada)

        remanente = restante_obligacion
        if remanente == ZERO:
            break
    excedente = ExcedentePago(remanente)
    tipo = _tipo_plan(afectadas, excedente, monto)
    plan = PlanPago(
        prestamo_id=prestamo_id,
        fecha_valor=fecha_valor,
        revision_prestamo=revision_prestamo,
        monto_pago_recibido=monto,
        obligaciones_afectadas=tuple(afectadas),
        aplicaciones=tuple(aplicaciones_globales),
        excedente=excedente,
        tipo=tipo,
    )
    plan.validar()
    return plan


def decidir_tratamiento_excedente(
    plan: PlanPago, tratamiento: TratamientoExcedente
) -> ExcedentePago:
    """Aplica la decisión comercial/contractual sin modificar el plan financiero."""
    plan.validar()
    if plan.excedente.monto == ZERO:
        if tratamiento is not TratamientoExcedente.SALDO_A_FAVOR:
            raise ErrorValidacion("No existe excedente al cual aplicar prepago")
    return ExcedentePago(plan.excedente.monto, tratamiento)


def _validar_conceptos_cobrables(
    obligaciones: Sequence[ObligacionSnapshot],
    devengamientos_por_cuota: Mapping[int, Sequence[Devengamiento]],
    orden: Sequence[ConceptoImputacion],
) -> None:
    conceptos_con_saldo: set[ConceptoImputacion] = set()
    for obligacion in obligaciones:
        for concepto in ConceptoImputacion:
            if obligacion.saldo.para_concepto(concepto) > ZERO:
                conceptos_con_saldo.add(concepto)
        for devengamiento in devengamientos_por_cuota.get(obligacion.cuota_id, ()):
            if devengamiento.monto > ZERO:
                conceptos_con_saldo.add(devengamiento.concepto)

    faltantes = sorted(
        (concepto.value for concepto in conceptos_con_saldo if concepto not in orden),
    )
    if faltantes:
        raise ErrorValidacion(
            "La política de waterfall omite conceptos con saldo exigible: "
            + ", ".join(faltantes)
        )


def _validar_orden(orden: Sequence[ConceptoImputacion]) -> None:
    normalizado = tuple(orden)
    permitidos = set(ConceptoImputacion)
    if any(concepto not in permitidos for concepto in normalizado):
        raise ErrorValidacion("El waterfall contiene un concepto inválido")
    if len(set(normalizado)) != len(normalizado):
        raise ErrorValidacion("El waterfall no puede repetir conceptos")
    if not normalizado:
        raise ErrorValidacion("El waterfall no puede ser vacío")


def _validar_obligaciones(obligaciones: Sequence[ObligacionSnapshot]) -> None:
    ids: set[int] = set()
    anterior: tuple[date, int] | None = None
    for obligacion in obligaciones:
        if obligacion.estado not in {"PENDIENTE", "PARCIAL", "PAGADA"}:
            raise ErrorValidacion(
                f"Estado de cuota inválido: {obligacion.estado}"
            )
        if obligacion.estado == "PAGADA" and obligacion.saldo.total > ZERO:
            raise ErrorInvariante(
                f"La cuota {obligacion.cuota_id} figura PAGADA con saldo pendiente"
            )
        if obligacion.estado in {"PENDIENTE", "PARCIAL"} and obligacion.saldo.total == ZERO:
            raise ErrorInvariante(
                f"La cuota {obligacion.cuota_id} figura {obligacion.estado} con saldo cero"
            )
        if obligacion.cuota_id in ids:
            raise ErrorValidacion(
                f"La cuota {obligacion.cuota_id} aparece más de una vez en el snapshot"
            )
        ids.add(obligacion.cuota_id)
        clave = (obligacion.vencimiento, obligacion.numero_cuota)
        if anterior is not None and clave < anterior:
            raise ErrorValidacion("Las obligaciones deben llegar cronológicamente ordenadas")
        anterior = clave


def _agregar_devengamientos(
    saldo: SaldoObligacion, devengamientos: Iterable[Devengamiento]
) -> SaldoObligacion:
    cambios = {concepto: ZERO for concepto in ConceptoImputacion}
    for dev in devengamientos:
        cambios[dev.concepto] = money(cambios[dev.concepto] + dev.monto)
    return SaldoObligacion(
        gasto=saldo.gasto + cambios[ConceptoImputacion.GASTO],
        penalizacion=saldo.penalizacion + cambios[ConceptoImputacion.PENALIZACION],
        mora=saldo.mora + cambios[ConceptoImputacion.MORA],
        interes=saldo.interes + cambios[ConceptoImputacion.INTERES],
        capital=saldo.capital + cambios[ConceptoImputacion.CAPITAL],
    )


def _restar_aplicaciones(
    saldo: SaldoObligacion, aplicaciones: Iterable[AplicacionPago]
) -> SaldoObligacion:
    cambios = {concepto: ZERO for concepto in ConceptoImputacion}
    for aplicacion in aplicaciones:
        cambios[aplicacion.concepto] = money(
            cambios[aplicacion.concepto] + aplicacion.monto
        )

    valores = {
        ConceptoImputacion.GASTO: money(saldo.gasto - cambios[ConceptoImputacion.GASTO]),
        ConceptoImputacion.PENALIZACION: money(
            saldo.penalizacion - cambios[ConceptoImputacion.PENALIZACION]
        ),
        ConceptoImputacion.MORA: money(saldo.mora - cambios[ConceptoImputacion.MORA]),
        ConceptoImputacion.INTERES: money(
            saldo.interes - cambios[ConceptoImputacion.INTERES]
        ),
        ConceptoImputacion.CAPITAL: money(
            saldo.capital - cambios[ConceptoImputacion.CAPITAL]
        ),
    }
    for concepto, valor in valores.items():
        if valor < ZERO:
            raise ErrorInvariante(
                f"Aplicación superior al saldo disponible de {concepto.value}"
            )
    return SaldoObligacion(
        gasto=valores[ConceptoImputacion.GASTO],
        penalizacion=valores[ConceptoImputacion.PENALIZACION],
        mora=valores[ConceptoImputacion.MORA],
        interes=valores[ConceptoImputacion.INTERES],
        capital=valores[ConceptoImputacion.CAPITAL],
    )


def _sumar_concepto(
    aplicaciones: Iterable[AplicacionPago], concepto: ConceptoImputacion
) -> Decimal:
    return money(sum((a.monto for a in aplicaciones if a.concepto is concepto), ZERO))


def _sumar_devengamiento(
    devengamientos: Iterable[Devengamiento], concepto: ConceptoImputacion
) -> Decimal:
    return money(sum((d.monto for d in devengamientos if d.concepto is concepto), ZERO))


def _hay_devengamiento_para_concepto(
    devengamientos: Sequence[Devengamiento], concepto: ConceptoImputacion
) -> bool:
    return any(d.concepto is concepto and d.monto > ZERO for d in devengamientos)


def _referencias_para_aplicacion(
    devengamientos: Sequence[Devengamiento], concepto: ConceptoImputacion
) -> tuple[str, ...]:
    return tuple(
        d.referencia
        for d in devengamientos
        if d.concepto is concepto and d.monto > ZERO and d.referencia
    )


def _tipo_plan(
    afectadas: Sequence[ObligacionAfectada], excedente: ExcedentePago, monto: Decimal
) -> TipoPlanPago:
    if excedente.monto > ZERO:
        return TipoPlanPago.ADELANTO
    if not afectadas:
        raise ErrorInvariante("Un pago válido debe afectar al menos una obligación")
    primera = afectadas[0]
    if primera.estado_anterior == "PARCIAL" and primera.estado_posterior == "PAGADA":
        return TipoPlanPago.COMPLEMENTO
    if primera.estado_posterior == "PARCIAL":
        return TipoPlanPago.PARCIAL
    if primera.estado_posterior == "PAGADA":
        return TipoPlanPago.CUOTA
    raise ErrorInvariante("No se pudo determinar el tipo del plan de pago")


# Nombre estable y explícito para consumidores externos al módulo.
PlanPagoV3 = PlanPago
