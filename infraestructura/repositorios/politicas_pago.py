"""Repositorio de la politica financiera versionada por prestamo."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

from dominio.politica_pago import (
    BaseMoraPago,
    EstrategiaObligacionesPago,
    PoliticaImputacionPago,
)
from dominio.tipos import ConceptoImputacion, ConvencionDias, rate


class PoliticaPagoRepo:
    def __init__(self, db) -> None:
        self.db = db

    def crear_inicial(
        self,
        prestamo_id: int,
        fecha_desde: date,
        *,
        usuario: str = "sistema",
        politica: PoliticaImputacionPago | None = None,
    ) -> int:
        politica = politica or PoliticaImputacionPago.canonica()
        fila = self.db.consultar_uno(
            "SELECT MAX(version) AS v FROM politicas_pago WHERE prestamo_id = ?",
            (prestamo_id,),
        )
        version = int(fila["v"] or 0) + 1 if fila else 1
        ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cursor = self.db.ejecutar(
            """
            INSERT INTO politicas_pago (
                prestamo_id, version, vigente_desde, vigente_hasta,
                estrategia_obligaciones, orden_waterfall,
                interes_compensatorio_post_vencimiento, mora_habilitada,
                mora_tasa_anual, mora_base, mora_convencion_dias,
                capitalizacion_intereses, creado_por, creado_en
            ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prestamo_id,
                version,
                fecha_desde.isoformat(),
                politica.estrategia_obligaciones.value,
                json.dumps([c.value for c in politica.orden_waterfall]),
                int(politica.interes_compensatorio_post_vencimiento),
                int(politica.mora_habilitada),
                str(politica.mora_tasa_anual),
                politica.mora_base.value,
                politica.mora_convencion_dias.value,
                int(politica.capitalizacion_intereses),
                usuario.strip() or "sistema",
                ahora,
            ),
        )
        return int(cursor.lastrowid)

    def obtener_vigente(
        self, prestamo_id: int, fecha: date | None = None
    ) -> PoliticaImputacionPago:
        fecha = fecha or date.today()
        fila = self.db.consultar_uno(
            """
            SELECT *
            FROM politicas_pago
            WHERE prestamo_id = ?
              AND vigente_desde <= ?
              AND (vigente_hasta IS NULL OR vigente_hasta > ?)
            ORDER BY version DESC
            LIMIT 1
            """,
            (prestamo_id, fecha.isoformat(), fecha.isoformat()),
        )
        if fila is None:
            raise RuntimeError(
                f"El préstamo {prestamo_id} no tiene política de pagos vigente"
            )
        return self._fila_a_politica(fila)

    def _fila_a_politica(self, fila) -> PoliticaImputacionPago:
        orden = tuple(
            ConceptoImputacion(valor)
            for valor in json.loads(fila["orden_waterfall"])
        )
        return PoliticaImputacionPago(
            estrategia_obligaciones=EstrategiaObligacionesPago(
                fila["estrategia_obligaciones"]
            ),
            orden_waterfall=orden,
            interes_compensatorio_post_vencimiento=bool(
                fila["interes_compensatorio_post_vencimiento"]
            ),
            mora_habilitada=bool(fila["mora_habilitada"]),
            mora_tasa_anual=rate(fila["mora_tasa_anual"]),
            mora_base=BaseMoraPago(fila["mora_base"]),
            mora_convencion_dias=ConvencionDias(fila["mora_convencion_dias"]),
            capitalizacion_intereses=bool(fila["capitalizacion_intereses"]),
        )
