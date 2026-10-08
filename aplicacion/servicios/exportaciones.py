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


    def reporte_financiero_persona_csv(
        self,
        persona_id: int,
        *,
        fecha_corte=None,
        inflacion_mensual_supuesta=None,
        horizonte_meses: int = 12,
    ) -> str:
        """Exporta el reporte consolidado de una persona en CSV."""
        kwargs = {"horizonte_meses": horizonte_meses}
        if fecha_corte is not None:
            kwargs["fecha_corte"] = fecha_corte
        if inflacion_mensual_supuesta is not None:
            kwargs["inflacion_mensual_supuesta"] = inflacion_mensual_supuesta

        reporte = ServicioReporteFinancieroPersona(self._db).obtener(
            persona_id,
            **kwargs,
        )
        filas: list[list[object]] = []

        def agregar(
            seccion: str,
            campo: str,
            valor: object,
            naturaleza: str,
            nota: str = "",
        ) -> None:
            filas.append(
                [
                    seccion,
                    campo,
                    "" if valor is None else str(valor),
                    naturaleza,
                    nota,
                ]
            )

        agregar("Contexto", "Persona", reporte.nombre_persona, "informativo")
        agregar("Contexto", "Fecha de corte", reporte.fecha_corte.isoformat(), "real")
        agregar(
            "Contexto",
            "Inflación mensual supuesta",
            reporte.inflacion_mensual_supuesta,
            "supuesto",
            "Usada solamente para expresar resultados reales.",
        )
        agregar("Contexto", "Horizonte", f"{reporte.horizonte_meses} meses", "supuesto")

        posicion = reporte.posicion
        agregar("Posición", "Capital invertido", posicion.capital_invertido, "real")
        agregar(
            "Posición",
            "Capital pendiente de deuda",
            posicion.capital_deuda_pendiente,
            "real",
        )
        agregar(
            "Posición",
            "Posición neta de capital",
            posicion.posicion_neta_capital,
            "derivado",
            "Capital invertido menos capital pendiente de deuda.",
        )
        agregar("Movimientos reales", "Cobros", posicion.cobros_reales, "real")
        agregar("Movimientos reales", "Pagos", posicion.pagos_reales, "real")
        agregar("Movimientos reales", "Flujo neto", posicion.flujo_neto_real, "derivado")

        plan = reporte.planificacion
        agregar("Plan futuro", "Cobros estimados", plan.cobros_estimados_total, "estimado")
        agregar("Plan futuro", "Pagos estimados", plan.pagos_estimados_total, "estimado")
        agregar(
            "Plan futuro",
            "Resultado futuro estimado",
            plan.neto_estimado_total,
            "estimado",
        )
        agregar(
            "Plan futuro",
            "Reserva de referencia",
            plan.reserva_sugerida,
            "estimado",
            "Cubre el peor déficit acumulado de movimientos conocidos, partiendo de cero.",
        )

        for mes in plan.movimientos_mensuales:
            agregar(
                "Plan mensual",
                mes.periodo.strftime("%Y-%m"),
                mes.neto_estimado,
                "estimado",
                (
                    f"Cobros={mes.cobros_estimados}; "
                    f"Pagos={mes.pagos_estimados}; "
                    f"Acumulado={mes.acumulado_estimado}"
                ),
            )

        for escenario in reporte.escenarios.resultados:
            agregar(
                "Escenario",
                f"{escenario.nombre} — inflación mensual",
                escenario.inflacion_mensual,
                "supuesto",
            )
            agregar(
                "Escenario",
                f"{escenario.nombre} — devaluación mensual",
                escenario.devaluacion_mensual,
                "supuesto",
            )
            agregar(
                "Escenario",
                f"{escenario.nombre} — neto nominal",
                escenario.neto_nominal,
                "escenario",
            )
            agregar(
                "Escenario",
                f"{escenario.nombre} — neto a precios de hoy",
                escenario.neto_real,
                "escenario",
            )
            agregar(
                "Escenario",
                f"{escenario.nombre} — neto USD",
                escenario.neto_usd,
                "escenario",
                "Solo disponible cuando existe una referencia USD válida.",
            )

        for indicador in (
            reporte.rendimiento.inversor,
            reporte.rendimiento.deudor,
        ):
            if indicador is None:
                continue
            agregar("Rendimiento", indicador.nombre, indicador.valor, "real", indicador.explicacion)
            agregar(
                "Rendimiento",
                f"{indicador.nombre} USD",
                indicador.valor_usd,
                "real",
                "Solo disponible con evidencia USD completa.",
            )
            agregar(
                "Rendimiento",
                f"{indicador.nombre} ajustado por inflación",
                indicador.rendimiento_real,
                "real",
                "Usa la inflación mensual supuesta del reporte.",
            )
            agregar(
                "Rendimiento",
                f"{indicador.rol} — movimientos reales",
                indicador.cantidad_flujos_reales,
                "evidencia",
                (
                    f"Entradas={indicador.cantidad_flujos_positivos}; "
                    f"Salidas={indicador.cantidad_flujos_negativos}"
                ),
            )

        return _csv(
            ["seccion", "campo", "valor", "naturaleza", "nota"],
            filas,
        )
