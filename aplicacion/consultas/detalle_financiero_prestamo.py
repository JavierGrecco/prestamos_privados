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
from dominio.tipos import ConceptoImputacion, money
from infraestructura.repositorios import PrestamoRepo


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

    def __init__(self, db) -> None:
        self._db = db

    def obtener(self, prestamo_id: int) -> DetalleFinancieroPrestamo:
        if prestamo_id <= 0:
            raise ValueError("prestamo_id debe ser positivo")

        prestamo_repo = PrestamoRepo(self._db)
        prestamo = prestamo_repo.obtener(prestamo_id)
        if prestamo is None:
            raise ValueError(f"El préstamo {prestamo_id} no existe")

        version_id = prestamo_repo.version_activa(prestamo_id)
        if version_id is None:
            raise ValueError(
                f"El préstamo {prestamo_id} no tiene una versión activa"
            )

        cuotas = self._cuotas(version_id)
        devengamientos = self._devengamientos(prestamo_id)
        recalculos = self._recalcudos(prestamo_id)
        eventos_capital = self._eventos_capital(prestamo_id)

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
            prestamo_id=prestamo.id,
            prestamo_numero=prestamo.numero,
            resumen=resumen,
            cuotas=cuotas,
            devengamientos=devengamientos,
            recalculos=recalculos,
            eventos_capital=eventos_capital,
        )

    def _cuotas(self, version_id: int) -> tuple[CuotaFinanciera, ...]:
        filas = self._db.consultar(
            """
            SELECT id, numero, fecha_vencimiento, estado,
                   capital_inicial, interes, capital, cuota, saldo,
                   monto_pendiente, interes_pendiente, capital_pendiente,
                   mora_pendiente, fue_mora, tuvo_pago_parcial,
                   fue_recalculada
            FROM cuotas
            WHERE version_id = ?
            ORDER BY numero, id
            """,
            (version_id,),
        )
        return tuple(
            CuotaFinanciera(
                id=int(f["id"]),
                numero=int(f["numero"]),
                vencimiento=date.fromisoformat(f["fecha_vencimiento"]),
                estado=str(f["estado"]),
                capital_inicial=Decimal(str(f["capital_inicial"])),
                interes_teorico=Decimal(str(f["interes"])),
                capital_teorico=Decimal(str(f["capital"])),
                cuota_teorica=Decimal(str(f["cuota"])),
                saldo_teorico=Decimal(str(f["saldo"])),
                monto_pendiente=Decimal(str(f["monto_pendiente"])),
                interes_pendiente=_pendiente(
                    f["interes_pendiente"],
                    f["interes"],
                    str(f["estado"]),
                    bool(f["tuvo_pago_parcial"]),
                ),
                capital_pendiente=_pendiente(
                    f["capital_pendiente"],
                    f["capital"],
                    str(f["estado"]),
                    bool(f["tuvo_pago_parcial"]),
                ),
                mora_pendiente=Decimal(str(f["mora_pendiente"])),
                fue_mora=bool(f["fue_mora"]),
                tuvo_pago_parcial=bool(f["tuvo_pago_parcial"]),
                fue_recalculada=bool(f["fue_recalculada"]),
            )
            for f in filas
        )

    def _devengamientos(
        self,
        prestamo_id: int,
    ) -> tuple[DevengamientoFinanciero, ...]:
        filas = self._db.consultar(
            """
            SELECT id, cuota_id, concepto, monto, fecha_desde, fecha_hasta,
                   origen, referencia, base, tasa_anual, dias, motor_version
            FROM devengamientos
            WHERE prestamo_id = ?
            ORDER BY fecha_hasta, id
            """,
            (prestamo_id,),
        )
        return tuple(
            DevengamientoFinanciero(
                id=int(f["id"]),
                cuota_id=int(f["cuota_id"]) if f["cuota_id"] is not None else None,
                concepto=str(f["concepto"]),
                monto=Decimal(str(f["monto"])),
                fecha_desde=date.fromisoformat(f["fecha_desde"]),
                fecha_hasta=date.fromisoformat(f["fecha_hasta"]),
                origen=str(f["origen"]),
                referencia=f["referencia"],
                base=Decimal(str(f["base"])),
                tasa_anual=Decimal(str(f["tasa_anual"])),
                dias=int(f["dias"]),
                motor_version=str(f["motor_version"]),
            )
            for f in filas
        )

    def _recalcudos(
        self,
        prestamo_id: int,
    ) -> tuple[RecalculoFinanciero, ...]:
        filas = self._db.consultar(
            """
            SELECT id, pago_id, tipo, fecha, capital_antes, capital_despues,
                   cuotas_antes, cuotas_despues, intereses_antes,
                   intereses_despues, detalle_json
            FROM historial_recalculos
            WHERE prestamo_id = ?
            ORDER BY fecha, id
            """,
            (prestamo_id,),
        )
        resultados = []
        for f in filas:
            antes = Decimal(str(f["intereses_antes"]))
            despues = Decimal(str(f["intereses_despues"]))
            detalle = None
            if f["detalle_json"]:
                try:
                    valor = json.loads(str(f["detalle_json"]))
                    detalle = valor if isinstance(valor, dict) else None
                except (TypeError, ValueError):
                    detalle = None

            resultados.append(
                RecalculoFinanciero(
                    id=int(f["id"]),
                    pago_id=int(f["pago_id"]),
                    tipo=str(f["tipo"]),
                    fecha=date.fromisoformat(str(f["fecha"])[:10]),
                    capital_antes=Decimal(str(f["capital_antes"])),
                    capital_despues=Decimal(str(f["capital_despues"])),
                    cuotas_antes=int(f["cuotas_antes"]),
                    cuotas_despues=int(f["cuotas_despues"]),
                    intereses_antes=antes,
                    intereses_despues=despues,
                    ahorro_intereses=money(antes - despues),
                    cuotas_ahorradas=int(f["cuotas_antes"]) - int(f["cuotas_despues"]),
                    detalle=detalle,
                )
            )
        return tuple(resultados)

    def _eventos_capital(
        self,
        prestamo_id: int,
    ) -> tuple[EventoCapitalFinanciero, ...]:
        filas = self._db.consultar(
            """
            SELECT
                p.id AS pago_id,
                p.fecha_valor,
                p.tipo_pago,
                i.monto
            FROM pagos p
            JOIN imputaciones i ON i.pago_id = p.id
            WHERE p.prestamo_id = ?
              AND p.estado = 'VALIDA'
              AND i.concepto = ?
            ORDER BY p.fecha_valor, p.id, i.id
            """,
            (prestamo_id, ConceptoImputacion.CAPITAL.value),
        )

        acumulados: dict[int, Decimal] = {}
        metadatos: dict[int, tuple[str, str, str]] = {}
        for fila in filas:
            pago_id = int(fila["pago_id"])
            acumulados[pago_id] = money(
                acumulados.get(pago_id, ZERO)
                + Decimal(str(fila["monto"]))
            )
            metadatos[pago_id] = (
                str(fila["fecha_valor"]),
                str(fila["tipo_pago"] or "CUOTA"),
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

        return tuple(
            sorted(eventos, key=lambda e: (e.fecha, e.pago_id))
        )


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

    def __init__(self, db) -> None:
        self._query = DetalleFinancieroPrestamoQuery(db)

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
