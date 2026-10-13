"""Adaptador SQLite de solo lectura para el análisis financiero.

Este módulo traduce repositorios y filas persistidas a los contratos públicos
de aplicación. No calcula rendimiento, escenarios ni importes financieros.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from aplicacion.puertos.analisis_financiero import (
    CobroLedgerAnalisis,
    CuotaAnalisis,
    PagoAsociadoCobroAnalisis,
    PagoDeudorAnalisis,
    ParticipacionAnalisis,
    PrestamoAnalisis,
    TasaActivaAnalisis,
)
from infraestructura.repositorios import ParticipacionRepo, PrestamoRepo


class AnalisisFinancieroSQLiteQuery:
    """Resuelve en SQLite las lecturas que necesita el análisis financiero."""

    def __init__(self, db) -> None:
        self._db = db
        self._prestamos = PrestamoRepo(db)
        self._participaciones = ParticipacionRepo(db)

    def prestamos_por_deudor(
        self, persona_id: int
    ) -> tuple[PrestamoAnalisis, ...]:
        return tuple(
            _prestamo_desde_modelo(p)
            for p in self._prestamos.listar(deudor_id=persona_id)
        )

    def participaciones_por_inversor(
        self, persona_id: int
    ) -> tuple[ParticipacionAnalisis, ...]:
        return tuple(
            _participacion_desde_modelo(p)
            for p in self._participaciones.por_inversor(persona_id)
        )

    def pagos_validos_de_prestamo(
        self, prestamo_id: int, hasta: date
    ) -> tuple[PagoDeudorAnalisis, ...]:
        filas = self._db.consultar(
            """
            SELECT fecha_real, monto_moneda_contractual, monto_usd_ref, tc_aplicado
            FROM pagos
            WHERE prestamo_id = ? AND estado = 'VALIDA' AND fecha_real <= ?
            ORDER BY fecha_real, id
            """,
            (prestamo_id, hasta.isoformat()),
        )
        return tuple(
            PagoDeudorAnalisis(
                fecha_real=date.fromisoformat(str(fila["fecha_real"])),
                monto_moneda_contractual=_decimal(
                    fila["monto_moneda_contractual"]
                ),
                monto_usd_ref=_decimal_opcional(fila["monto_usd_ref"]),
                tc_aplicado=_decimal_opcional(fila["tc_aplicado"]),
            )
            for fila in filas
        )

    def cobros_de_inversor(
        self, persona_id: int, hasta: date
    ) -> tuple[CobroLedgerAnalisis, ...]:
        filas = self._db.consultar(
            """
            SELECT debe, fecha, metadata
            FROM ledger
            WHERE entidad = 'INVERSOR'
              AND entidad_id = ?
              AND tipo_movimiento = 'COBRO_PAGO'
              AND fecha <= ?
            ORDER BY fecha, id
            """,
            (persona_id, hasta.isoformat()),
        )
        return tuple(
            CobroLedgerAnalisis(
                debe=_decimal(fila["debe"]),
                fecha=date.fromisoformat(str(fila["fecha"])[:10]),
                metadata=(
                    str(fila["metadata"])
                    if fila["metadata"] is not None
                    else None
                ),
            )
            for fila in filas
        )

    def pago_para_cobro(
        self, pago_id: int
    ) -> PagoAsociadoCobroAnalisis | None:
        fila = self._db.consultar_uno(
            """
            SELECT p.prestamo_id, p.fecha_real, p.monto_usd_ref, p.tc_aplicado,
                   pr.numero AS prestamo_numero
            FROM pagos p
            LEFT JOIN prestamos pr ON pr.id = p.prestamo_id
            WHERE p.id = ?
            """,
            (pago_id,),
        )
        if fila is None:
            return None
        return PagoAsociadoCobroAnalisis(
            prestamo_id=int(fila["prestamo_id"]),
            fecha_real=date.fromisoformat(str(fila["fecha_real"])),
            monto_usd_ref=_decimal_opcional(fila["monto_usd_ref"]),
            tc_aplicado=_decimal_opcional(fila["tc_aplicado"]),
            prestamo_numero=(
                str(fila["prestamo_numero"])
                if fila["prestamo_numero"] is not None
                else "—"
            ),
        )

    def numero_prestamo(self, prestamo_id: int) -> str:
        if prestamo_id <= 0:
            return "—"
        fila = self._db.consultar_uno(
            "SELECT numero FROM prestamos WHERE id = ?",
            (prestamo_id,),
        )
        return "—" if fila is None else str(fila["numero"])

    def prestamo_por_id(self, prestamo_id: int) -> PrestamoAnalisis | None:
        prestamo = self._prestamos.obtener(prestamo_id)
        return None if prestamo is None else _prestamo_desde_modelo(prestamo)

    def version_activa(self, prestamo_id: int) -> int | None:
        return self._prestamos.version_activa(prestamo_id)

    def cuotas_proyectadas(
        self, version_id: int, desde: date
    ) -> tuple[CuotaAnalisis, ...]:
        filas = self._db.consultar(
            """
            SELECT id, numero, fecha_vencimiento, estado, cuota, capital,
                   monto_pendiente, interes_pendiente, capital_pendiente,
                   mora_pendiente, tuvo_pago_parcial
            FROM cuotas
            WHERE version_id = ?
              AND estado IN ('PENDIENTE', 'PARCIAL', 'VENCIDA')
              AND fecha_vencimiento >= ?
            ORDER BY fecha_vencimiento, numero, id
            """,
            (version_id, desde.isoformat()),
        )
        return tuple(_cuota_desde_fila(fila) for fila in filas)

    def cuotas_pendientes_capital(
        self, version_id: int
    ) -> tuple[CuotaAnalisis, ...]:
        filas = self._db.consultar(
            """
            SELECT id, numero, fecha_vencimiento, estado, cuota, capital,
                   monto_pendiente, interes_pendiente, capital_pendiente,
                   mora_pendiente, tuvo_pago_parcial
            FROM cuotas
            WHERE version_id = ?
              AND estado IN ('PENDIENTE', 'PARCIAL', 'VENCIDA')
            ORDER BY numero, id
            """,
            (version_id,),
        )
        return tuple(_cuota_desde_fila(fila) for fila in filas)

    def tasa_activa(self, prestamo_id: int) -> TasaActivaAnalisis | None:
        tasa = self._prestamos.info_tasa_activa(prestamo_id)
        if tasa is None:
            return None
        return TasaActivaAnalisis(
            modalidad=str(tasa["modalidad"]),
            tasa_anual=_decimal(tasa["tasa_anual"]),
        )


def _prestamo_desde_modelo(prestamo) -> PrestamoAnalisis:
    return PrestamoAnalisis(
        id=int(prestamo.id),
        numero=str(prestamo.numero),
        estado=str(prestamo.estado),
        fecha_inicio=prestamo.fecha_inicio,
        tc_inicial=_decimal_opcional(prestamo.tc_inicial),
        capital_original=_decimal(prestamo.capital_original),
        plazo_meses=int(prestamo.plazo_meses),
        sistema=str(prestamo.sistema),
    )


def _participacion_desde_modelo(participacion) -> ParticipacionAnalisis:
    return ParticipacionAnalisis(
        prestamo_id=int(participacion.prestamo_id),
        estado=str(participacion.estado),
        capital_aportado=_decimal(participacion.capital_aportado),
        fecha_aporte=participacion.fecha_aporte,
        tc_aporte=_decimal_opcional(participacion.tc_aporte),
        capital_usd_ref=_decimal_opcional(participacion.capital_usd_ref),
        porcentaje=_decimal(participacion.porcentaje),
    )


def _cuota_desde_fila(fila) -> CuotaAnalisis:
    return CuotaAnalisis(
        id=int(fila["id"]),
        numero=int(fila["numero"]),
        fecha_vencimiento=date.fromisoformat(str(fila["fecha_vencimiento"])),
        estado=str(fila["estado"]),
        cuota=_decimal(fila["cuota"]),
        capital=_decimal(fila["capital"]),
        monto_pendiente=_decimal(fila["monto_pendiente"]),
        interes_pendiente=_decimal(fila["interes_pendiente"]),
        capital_pendiente=_decimal(fila["capital_pendiente"]),
        mora_pendiente=_decimal(fila["mora_pendiente"]),
        tuvo_pago_parcial=bool(fila["tuvo_pago_parcial"]),
    )


def _decimal(valor) -> Decimal:
    """Normaliza cantidades persistidas sin pasar por float."""
    return Decimal(str(valor if valor is not None else "0"))


def _decimal_opcional(valor) -> Decimal | None:
    if valor is None or valor == "":
        return None
    return Decimal(str(valor))


__all__ = ["AnalisisFinancieroSQLiteQuery"]
