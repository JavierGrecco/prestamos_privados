"""Exportaciones CSV de datos de solo lectura.

Las exportaciones consumen read models/servicios existentes y no modifican
SQLite ni recalculan hechos financieros.
"""
from __future__ import annotations

import csv
import io
import json

from aplicacion.consultas.detalle_financiero_prestamo import (
    ServicioDetalleFinancieroPrestamo,
)
from aplicacion.servicios.auditoria import FiltrosAuditoria, ServicioAuditoria
from aplicacion.servicios.personas import ServicioPersonas


def _csv(headers: list[str], rows) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue()


class ServicioExportaciones:
    """Genera representaciones CSV reproducibles a partir de datos persistidos."""

    def __init__(self, db) -> None:
        self._db = db
        self._auditoria = ServicioAuditoria(db)
        self._detalle = ServicioDetalleFinancieroPrestamo(db)
        self._personas = ServicioPersonas(db)

    def auditoria_csv(self, filtros: FiltrosAuditoria | None = None) -> str:
        entradas = self._auditoria.listar(filtros)
        return _csv(
            [
                "id",
                "fecha",
                "usuario",
                "operacion",
                "entidad",
                "entidad_id",
                "motivo",
                "correlacion_id",
                "datos_anteriores",
                "datos_nuevos",
            ],
            [
                [
                    e.id,
                    e.fecha,
                    e.usuario,
                    e.operacion,
                    e.entidad,
                    e.entidad_id if e.entidad_id is not None else "",
                    e.motivo or "",
                    e.correlacion_id,
                    e.datos_anteriores or "",
                    e.datos_nuevos or "",
                ]
                for e in entradas
            ],
        )

    def personas_csv(self) -> str:
        personas = self._personas.listar()
        return _csv(
            [
                "id",
                "nombre",
                "apellido",
                "documento",
                "telefono",
                "email",
                "domicilio",
                "estado",
                "roles",
            ],
            [
                [
                    p.id,
                    p.nombre,
                    p.apellido,
                    p.documento or "",
                    p.telefono or "",
                    p.email or "",
                    p.domicilio or "",
                    p.estado,
                    ", ".join(self._personas.roles(p.id)),
                ]
                for p in personas
            ],
        )

    def amortizacion_csv(self, prestamo_id: int) -> str:
        detalle = self._detalle.obtener(prestamo_id)
        return _csv(
            [
                "prestamo_id",
                "prestamo_numero",
                "cuota_id",
                "numero",
                "vencimiento",
                "estado",
                "capital_inicial",
                "interes_teorico",
                "capital_teorico",
                "cuota_teorica",
                "saldo_teorico",
                "monto_pendiente",
                "interes_pendiente",
                "capital_pendiente",
                "mora_pendiente",
                "fue_mora",
                "tuvo_pago_parcial",
                "fue_recalculada",
            ],
            [
                [
                    detalle.prestamo_id,
                    detalle.prestamo_numero,
                    c.id,
                    c.numero,
                    c.vencimiento.isoformat(),
                    c.estado,
                    str(c.capital_inicial),
                    str(c.interes_teorico),
                    str(c.capital_teorico),
                    str(c.cuota_teorica),
                    str(c.saldo_teorico),
                    str(c.monto_pendiente),
                    str(c.interes_pendiente),
                    str(c.capital_pendiente),
                    str(c.mora_pendiente),
                    c.fue_mora,
                    c.tuvo_pago_parcial,
                    c.fue_recalculada,
                ]
                for c in detalle.cuotas
            ],
        )

    def metadata_json(self, prestamo_id: int) -> str:
        """Devuelve metadata mínima para acompañar una exportación."""
        detalle = self._detalle.obtener(prestamo_id)
        return json.dumps(
            {
                "prestamo_id": detalle.prestamo_id,
                "prestamo_numero": detalle.prestamo_numero,
                "cuotas_exportadas": len(detalle.cuotas),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
