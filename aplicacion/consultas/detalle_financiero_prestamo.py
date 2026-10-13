"""Read model del detalle financiero profundo de un préstamo.

Solo consulta datos persistidos. No modifica SQLite ni vuelve a ejecutar las
reglas financieras para reconstruir hechos históricos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
import json

from dominio.trayectoria_capital_v3 import (
    EventoReduccionCapital,
    ResultadoTrayectoriaCapital,
    construir_trayectoria_capital_real,
)
from dominio.tipos import money
from aplicacion.puertos.detalle_financiero_prestamo import (
    ConsultaDetalleFinancieroPrestamo,
    CuotaDetalleLectura,
    DevengamientoDetalleLectura,
    ImputacionCapitalDetalleLectura,
    RecalculoDetalleLectura,
)


ZERO = Decimal("0.00")


@dataclass(frozen=True)
class CuotaFinanciera:
    id: int
    numero: int
    vencimiento: date
    estado: str
    capital_inicial: Decimal
    interes_teorico: Decimal
    capital_teorico: Decimal
    cuota_teorica: Decimal
    saldo_teorico: Decimal
    monto_pendiente: Decimal
    interes_pendiente: Decimal
    capital_pendiente: Decimal
    mora_pendiente: Decimal
    fue_mora: bool
    tuvo_pago_parcial: bool
    fue_recalculada: bool


@dataclass(frozen=True)
class DevengamientoFinanciero:
    id: int
    cuota_id: int | None
    concepto: str
    monto: Decimal
    fecha_desde: date
    fecha_hasta: date
    origen: str
    referencia: str | None
    base: Decimal
    tasa_anual: Decimal
    dias: int
    motor_version: str


@dataclass(frozen=True)
class RecalculoFinanciero:
    id: int
    pago_id: int
    tipo: str
    fecha: date
    capital_antes: Decimal
    capital_despues: Decimal
    cuotas_antes: int
    cuotas_despues: int
    intereses_antes: Decimal
    intereses_despues: Decimal
    ahorro_intereses: Decimal
    cuotas_ahorradas: int
    detalle: dict | None


@dataclass(frozen=True)
class EventoCapitalFinanciero:
    pago_id: int
    fecha: date
    monto: Decimal
    tipo_pago: str
    referencia: str


@dataclass(frozen=True)
class ResumenCapitalFinanciero:
    capital_original: Decimal
    capital_aplicado: Decimal
    capital_pendiente: Decimal
    porcentaje_amortizado: Decimal
    interes_devengado: Decimal
    interes_ahorrado_por_recalculos: Decimal
    trayectoria: ResultadoTrayectoriaCapital


@dataclass(frozen=True)
class DetalleFinancieroPrestamo:
    prestamo_id: int
    prestamo_numero: str
    resumen: ResumenCapitalFinanciero
    cuotas: tuple[CuotaFinanciera, ...]
    devengamientos: tuple[DevengamientoFinanciero, ...]
    recalculos: tuple[RecalculoFinanciero, ...]
    eventos_capital: tuple[EventoCapitalFinanciero, ...]


class DetalleFinancieroPrestamoQuery:
    """Consulta de solo lectura para el detalle financiero."""

    def __init__(self, consulta: ConsultaDetalleFinancieroPrestamo) -> None:
        self._consulta = consulta

    def obtener(self, prestamo_id: int) -> DetalleFinancieroPrestamo:
        if prestamo_id <= 0:
            raise ValueError("prestamo_id debe ser positivo")

        prestamo = self._consulta.obtener_prestamo(prestamo_id)
        if prestamo is None:
            raise ValueError(f"El préstamo {prestamo_id} no existe")

        version_id = self._consulta.version_activa(prestamo_id)
        if version_id is None:
            raise ValueError(
                f"El préstamo {prestamo_id} no tiene una versión activa"
            )

        cuotas = self._cuotas(self._consulta.cuotas(version_id))
        devengamientos = self._devengamientos(
            self._consulta.devengamientos(prestamo_id)
        )
        recalculos = self._recalcudos(self._consulta.recalculos(prestamo_id))
        eventos_capital = self._eventos_capital(
            self._consulta.imputaciones_capital(prestamo_id)
        )

        capital_pendiente = money(
            sum((c.capital_pendiente for c in cuotas), ZERO)
        )
        capital_aplicado = money(
            sum((e.monto for e in eventos_capital), ZERO)
        )
        porcentaje = (
            money(
                capital_aplicado
                / prestamo.capital_original
                * Decimal("100")
            )
            if prestamo.capital_original > ZERO
            else ZERO
        )

        trayectoria = _construir_trayectoria(
            prestamo.capital_original,
            prestamo.fecha_inicio,
            eventos_capital,
        )

        resumen = ResumenCapitalFinanciero(
            capital_original=money(prestamo.capital_original),
            capital_aplicado=capital_aplicado,
            capital_pendiente=capital_pendiente,
            porcentaje_amortizado=porcentaje,
            interes_devengado=money(
                sum(
                    (d.monto for d in devengamientos if d.concepto == "INTERES"),
                    ZERO,
                )
            ),
            interes_ahorrado_por_recalculos=money(
                sum((r.ahorro_intereses for r in recalculos), ZERO)
            ),
            trayectoria=trayectoria,
        )

        return DetalleFinancieroPrestamo(
            prestamo_id=prestamo.prestamo_id,
            prestamo_numero=prestamo.numero,
            resumen=resumen,
            cuotas=cuotas,
            devengamientos=devengamientos,
            recalculos=recalculos,
            eventos_capital=eventos_capital,
        )

    def _cuotas(
        self,
        filas: tuple[CuotaDetalleLectura, ...] | list[CuotaDetalleLectura],
    ) -> tuple[CuotaFinanciera, ...]:
        return tuple(
            CuotaFinanciera(
                id=f.id,
                numero=f.numero,
                vencimiento=f.vencimiento,
                estado=f.estado,
                capital_inicial=f.capital_inicial,
                interes_teorico=f.interes,
                capital_teorico=f.capital,
                cuota_teorica=f.cuota,
                saldo_teorico=f.saldo,
                monto_pendiente=f.monto_pendiente,
                interes_pendiente=_pendiente(
                    f.interes_pendiente,
                    f.interes,
                    f.estado,
                    f.tuvo_pago_parcial,
                ),
                capital_pendiente=_pendiente(
                    f.capital_pendiente,
                    f.capital,
                    f.estado,
                    f.tuvo_pago_parcial,
                ),
                mora_pendiente=f.mora_pendiente or ZERO,
                fue_mora=f.fue_mora,
                tuvo_pago_parcial=f.tuvo_pago_parcial,
                fue_recalculada=f.fue_recalculada,
            )
            for f in filas
        )

    def _devengamientos(
        self,
        filas: tuple[DevengamientoDetalleLectura, ...] | list[DevengamientoDetalleLectura],
    ) -> tuple[DevengamientoFinanciero, ...]:
        return tuple(
            DevengamientoFinanciero(
                id=f.id,
                cuota_id=f.cuota_id,
                concepto=f.concepto,
                monto=f.monto,
                fecha_desde=f.fecha_desde,
                fecha_hasta=f.fecha_hasta,
                origen=f.origen,
                referencia=f.referencia,
                base=f.base,
                tasa_anual=f.tasa_anual,
                dias=f.dias,
                motor_version=f.motor_version,
            )
            for f in filas
        )

    def _recalcudos(
        self,
        filas: tuple[RecalculoDetalleLectura, ...] | list[RecalculoDetalleLectura],
    ) -> tuple[RecalculoFinanciero, ...]:
        resultados = []
        for f in filas:
            detalle = None
            if f.detalle_json:
                try:
                    valor = json.loads(f.detalle_json)
                    detalle = valor if isinstance(valor, dict) else None
                except (TypeError, ValueError):
                    detalle = None

            resultados.append(
                RecalculoFinanciero(
                    id=f.id,
                    pago_id=f.pago_id,
                    tipo=f.tipo,
                    fecha=f.fecha,
                    capital_antes=f.capital_antes,
                    capital_despues=f.capital_despues,
                    cuotas_antes=f.cuotas_antes,
                    cuotas_despues=f.cuotas_despues,
                    intereses_antes=f.intereses_antes,
                    intereses_despues=f.intereses_despues,
                    ahorro_intereses=money(f.intereses_antes - f.intereses_despues),
                    cuotas_ahorradas=f.cuotas_antes - f.cuotas_despues,
                    detalle=detalle,
                )
            )
        return tuple(resultados)

    def _eventos_capital(
        self,
        filas: tuple[ImputacionCapitalDetalleLectura, ...] | list[ImputacionCapitalDetalleLectura],
    ) -> tuple[EventoCapitalFinanciero, ...]:
        acumulados: dict[int, Decimal] = {}
        metadatos: dict[int, tuple[str, str, str]] = {}
        for fila in filas:
            pago_id = fila.pago_id
            acumulados[pago_id] = money(
                acumulados.get(pago_id, ZERO) + fila.monto
            )
            metadatos[pago_id] = (
                fila.fecha_valor.isoformat(),
                str(fila.tipo_pago or "CUOTA"),
                f"PAGO:{pago_id}",
            )

        eventos = []
        for pago_id, monto in acumulados.items():
            fecha_texto, tipo_pago, referencia = metadatos[pago_id]
            if monto <= ZERO:
                continue
            eventos.append(
                EventoCapitalFinanciero(
                    pago_id=pago_id,
                    fecha=date.fromisoformat(fecha_texto),
                    monto=monto,
                    tipo_pago=tipo_pago,
                    referencia=referencia,
                )
            )

        return tuple(sorted(eventos, key=lambda e: (e.fecha, e.pago_id)))


def _pendiente(
    pendiente,
    contractual,
    estado: str,
    tuvo_pago_parcial: bool,
) -> Decimal:
    valor = Decimal(str(pendiente or "0"))
    if valor == ZERO and estado == "PENDIENTE" and not tuvo_pago_parcial:
        return Decimal(str(contractual or "0"))
    return valor


class ServicioDetalleFinancieroPrestamo:
    """Caso de uso de lectura del detalle financiero."""

    def __init__(self, consulta: ConsultaDetalleFinancieroPrestamo) -> None:
        self._query = DetalleFinancieroPrestamoQuery(consulta)

    def obtener(self, prestamo_id: int) -> DetalleFinancieroPrestamo:
        return self._query.obtener(prestamo_id)


def _construir_trayectoria(
    capital_original: Decimal,
    fecha_inicio: date,
    eventos: tuple[EventoCapitalFinanciero, ...],
) -> ResultadoTrayectoriaCapital:
    eventos_dominio = tuple(
        EventoReduccionCapital(
            fecha_valor=e.fecha,
            monto=e.monto,
            referencia=e.referencia,
        )
        for e in eventos
    )
    hasta = (
        eventos[-1].fecha + timedelta(days=1)
        if eventos
        else fecha_inicio
    )
    if hasta == fecha_inicio:
        # El período vacío todavía necesita un punto inicial válido.
        return construir_trayectoria_capital_real(
            capital_inicial=capital_original,
            fecha_inicio_contrato=fecha_inicio,
            fecha_desde=fecha_inicio,
            fecha_hasta=fecha_inicio,
            eventos=eventos_dominio,
        )

    return construir_trayectoria_capital_real(
        capital_inicial=capital_original,
        fecha_inicio_contrato=fecha_inicio,
        fecha_desde=fecha_inicio,
        fecha_hasta=hasta,
        eventos=eventos_dominio,
    )
