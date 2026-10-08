"""Repositorio de la politica financiera versionada por prestamo."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from uuid import uuid4

from dominio.politica_pago import (
    BaseMoraPago,
    EstrategiaObligacionesPago,
    PoliticaImputacionPago,
)
from dominio.tipos import ConceptoImputacion, ConvencionDias, rate
from .auditoria import AuditoriaRepo


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

    def crear_version(
        self,
        prestamo_id: int,
        fecha_desde: date,
        politica: PoliticaImputacionPago,
        *,
        usuario: str,
    ) -> int:
        """Crea una nueva version atomica y auditable."""
        usuario_limpio = usuario.strip()
        if not usuario_limpio:
            raise ValueError("Se requiere un usuario para cambiar la politica")

        with self.db.transaccion():
            actual = self.db.consultar_uno(
                """
                SELECT id, version, vigente_desde
                FROM politicas_pago
                WHERE prestamo_id = ?
                  AND vigente_hasta IS NULL
                ORDER BY version DESC
                LIMIT 1
                """,
                (prestamo_id,),
            )
            if actual is not None:
                if fecha_desde.isoformat() <= actual["vigente_desde"]:
                    raise ValueError(
                        "La nueva vigencia debe comenzar despues de la version activa"
                    )
                version = int(actual["version"]) + 1
                self.db.ejecutar(
                    "UPDATE politicas_pago SET vigente_hasta = ? WHERE id = ?",
                    (fecha_desde.isoformat(), actual["id"]),
                )
            else:
                version = 1

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
                    usuario_limpio,
                    ahora,
                ),
            )
            nuevo_id = int(cursor.lastrowid)

            AuditoriaRepo(self.db).registrar(
                usuario_limpio,
                "POLITICA_PAGO_VERSION_CREADA",
                "POLITICA_PAGO",
                nuevo_id,
                uuid4().hex,
                None,
                {
                    "prestamo_id": prestamo_id,
                    "version": version,
                    "vigente_desde": fecha_desde.isoformat(),
                    "orden_waterfall": [c.value for c in politica.orden_waterfall],
                    "interes_compensatorio_post_vencimiento": (
                        politica.interes_compensatorio_post_vencimiento
                    ),
                    "mora_habilitada": politica.mora_habilitada,
                    "mora_tasa_anual": str(politica.mora_tasa_anual),
                    "mora_base": politica.mora_base.value,
                    "mora_convencion_dias": politica.mora_convencion_dias.value,
                    "capitalizacion_intereses": politica.capitalizacion_intereses,
                },
                "Cambio contractual de politica de pagos",
            )
            return nuevo_id

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
