"""Adaptador de lectura SQLite para los datos básicos de la ficha."""

from __future__ import annotations

from decimal import Decimal

from aplicacion.consultas.ficha_prestamo import (
    PagoFicha,
    PrestamoFicha,
    TasaActivaFicha,
)
from infraestructura.repositorios import PagoRepo, PrestamoRepo


class FichaPrestamoSQLite:
    """Traduce los repositorios actuales al contrato de la consulta."""

    def __init__(self, db) -> None:
        self._db = db
        self._prestamos = PrestamoRepo(db)
        self._pagos = PagoRepo(db)

    def obtener_prestamo(self, prestamo_id: int) -> PrestamoFicha | None:
        prestamo = self._prestamos.obtener(prestamo_id)
        if prestamo is None:
            return None
        return PrestamoFicha(
            id=int(prestamo.id),
            numero=str(prestamo.numero),
            deudor_id=(
                int(prestamo.deudor_id)
                if prestamo.deudor_id is not None
                else None
            ),
            capital_original=prestamo.capital_original,
            plazo_meses=int(prestamo.plazo_meses),
            sistema=str(prestamo.sistema),
            fecha_inicio=prestamo.fecha_inicio,
            estado=str(prestamo.estado),
            destino=prestamo.destino,
        )

    def obtener_tasa_activa(
        self, prestamo_id: int
    ) -> TasaActivaFicha | None:
        version_id = self._prestamos.version_activa(prestamo_id)
        if not version_id:
            return None

        fila = self._db.consultar_uno(
            "SELECT tasa_anual, modalidad_tasa FROM versiones_tasa WHERE id = ?",
            (version_id,),
        )
        if not fila:
            return None

        return TasaActivaFicha(
            tasa_anual=Decimal(str(fila["tasa_anual"])),
            modalidad_tasa=str(fila["modalidad_tasa"]),
        )

    def listar_pagos(self, prestamo_id: int) -> tuple[PagoFicha, ...]:
        # PagoRepo devuelve fecha_real e ID en orden ascendente; la tarjeta debe
        # seguir mostrando los mismos pagos y en el mismo orden.
        return tuple(
            PagoFicha(
                estado=str(pago.estado),
                fecha_real=pago.fecha_real,
                monto_moneda_pago=pago.monto_moneda_pago,
                tipo_pago=str(getattr(pago, "tipo_pago", "CUOTA") or "CUOTA"),
                medio=pago.medio,
                nota=pago.nota,
            )
            for pago in self._pagos.por_prestamo(prestamo_id)
        )


__all__ = ["FichaPrestamoSQLite"]
