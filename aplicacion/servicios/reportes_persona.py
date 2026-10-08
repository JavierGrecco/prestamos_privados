"""Reportes financieros por persona.

Construye una foto coherente de la información financiera administrada por la
aplicación y ofrece formatos humano y técnico.

El servicio solo compone read models existentes. No escribe SQLite y no
recalcula reglas financieras.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aplicacion.consultas.escenarios_persona import (
    ResultadoEscenariosPersona,
    ServicioEscenariosPersona,
)
from aplicacion.consultas.planificacion_financiera_persona import (
    PlanificacionFinancieraPersona,
    ServicioPlanificacionFinancieraPersona,
)
from aplicacion.consultas.posicion_financiera_persona import (
    PosicionFinancieraPersona,
    ServicioPosicionFinancieraPersona,
)
from aplicacion.consultas.rendimiento_financiero_persona import (
    RendimientoFinancieroPersona,
    ServicioRendimientoFinancieroPersona,
)
from infraestructura.db import BaseDatos
from infraestructura.repositorios import PersonaRepo


@dataclass(frozen=True)
class ReportePersona:
    persona_id: int
    nombre: str
    fecha_corte: date
    inflacion_mensual_supuesto: Decimal
    horizonte_meses: int
    posicion: PosicionFinancieraPersona
    planificacion: PlanificacionFinancieraPersona
    rendimiento: RendimientoFinancieroPersona
    escenarios: ResultadoEscenariosPersona


class ServicioReportesPersona:
    """Genera reportes reproducibles a partir de read models existentes."""

    def __init__(self, db: BaseDatos) -> None:
        self._personas = PersonaRepo(db)
        self._posicion = ServicioPosicionFinancieraPersona(db)
        self._plan = ServicioPlanificacionFinancieraPersona(db)
        self._rendimiento = ServicioRendimientoFinancieroPersona(db)
        self._escenarios = ServicioEscenariosPersona(db)

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        inflacion_mensual_supuesto: Decimal = Decimal('0.05'),
        horizonte_meses: int = 12,
    ) -> ReportePersona:
        persona = self._personas.obtener(persona_id)
        if persona is None:
            raise ValueError(f'La persona {persona_id} no existe')

        corte = fecha_corte or date.today()
        inflacion = Decimal(str(inflacion_mensual_supuesto))

        nombre = getattr(persona, 'nombre_completo', None) or (
            f'{persona.nombre} {persona.apellido}'.strip()
        )

        return ReportePersona(
            persona_id=persona_id,
            nombre=nombre,
            fecha_corte=corte,
            inflacion_mensual_supuesto=inflacion,
            horizonte_meses=horizonte_meses,
            posicion=self._posicion.obtener(
                persona_id,
                fecha_corte=corte,
            ),
            planificacion=self._plan.obtener(
                persona_id,
                fecha_corte=corte,
                horizonte_meses=horizonte_meses,
            ),
            rendimiento=self._rendimiento.obtener(
                persona_id,
                fecha_corte=corte,
                inflacion_mensual_supuesto=inflacion,
            ),
            escenarios=self._escenarios.obtener(
                persona_id,
                fecha_corte=corte,
                horizonte_meses=horizonte_meses,
            ),
        )

    def json(self, reporte: ReportePersona) -> str:
        return json.dumps(
            _a_dict(reporte),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    def csv_resumen(self, reporte: ReportePersona) -> str:
        rows = _filas_resumen(reporte)
        buffer = io.StringIO(newline='')
        writer = csv.writer(buffer, lineterminator='\n')
        writer.writerow(['seccion', 'indicador', 'valor', 'naturaleza'])
        writer.writerows(rows)
        return buffer.getvalue()

    def markdown(self, reporte: ReportePersona) -> str:
        return _markdown_reporte(reporte)


def _serializar(valor):
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, tuple):
        return [_serializar(x) for x in valor]
    if isinstance(valor, list):
        return [_serializar(x) for x in valor]
    if hasattr(valor, '__dataclass_fields__'):
        return {
            campo: _serializar(getattr(valor, campo))
            for campo in valor.__dataclass_fields__
        }
    return valor


def _a_dict(reporte: ReportePersona) -> dict:
    return {
        'persona_id': reporte.persona_id,
        'nombre': reporte.nombre,
        'fecha_corte': reporte.fecha_corte.isoformat(),
        'inflacion_mensual_supuesto': str(reporte.inflacion_mensual_supuesto),
        'horizonte_meses': reporte.horizonte_meses,
        'posicion': _serializar(reporte.posicion),
        'planificacion': _serializar(reporte.planificacion),
        'rendimiento': _serializar(reporte.rendimiento),
        'escenarios': _serializar(reporte.escenarios),
    }


def _fmt_pesos(valor: Decimal | None) -> str:
    if valor is None:
        return 'No disponible'
    negativo = valor < 0
    entero, decimales = f'{abs(valor):.2f}'.split('.')
    entero = f'{int(entero):,}'.replace(',', '.')
    return f'{"-" if negativo else ""}$ {entero},{decimales}'


def _fmt_usd(valor: Decimal | None) -> str:
    if valor is None:
        return 'No disponible'
    return f'USD {valor:,.2f}'


def _fmt_pct(valor: Decimal | None) -> str:
    if valor is None:
        return 'No disponible'
    return f'{valor * Decimal("100"):.2f}%'


def _filas_resumen(reporte: ReportePersona) -> list[list[str]]:
    p = reporte.posicion
    plan = reporte.planificacion
    r = reporte.rendimiento
    e = reporte.escenarios
    filas = [
        ['Posición', 'Capital invertido', _fmt_pesos(p.capital_invertido), 'Real'],
        ['Posición', 'Capital de deuda pendiente', _fmt_pesos(p.capital_deuda_pendiente), 'Real'],
        ['Posición', 'Posición neta de capital', _fmt_pesos(p.posicion_neta_capital), 'Derivado'],
        ['Posición', 'Cobros reales registrados', _fmt_pesos(p.cobros_reales), 'Real'],
        ['Posición', 'Pagos reales registrados', _fmt_pesos(p.pagos_reales), 'Real'],
        ['Planificación', 'Cobros futuros estimados', _fmt_pesos(plan.cobros_estimados_total), 'Estimado'],
        ['Planificación', 'Pagos futuros estimados', _fmt_pesos(plan.pagos_estimados_total), 'Estimado'],
        ['Planificación', 'Resultado futuro estimado', _fmt_pesos(plan.neto_estimado_total), 'Estimado'],
        ['Planificación', 'Reserva sugerida', _fmt_pesos(plan.reserva_sugerida), 'Referencia'],
    ]
    if r.inversor is not None:
        filas.extend([
            ['Rendimiento', 'Rendimiento anualizado', _fmt_pct(r.inversor.valor), 'Histórico'],
            ['Rendimiento', 'Rendimiento ajustado por inflación', _fmt_pct(r.inversor.rendimiento_real), 'Histórico con supuesto'],
            ['Rendimiento', 'Rendimiento anualizado USD', _fmt_pct(r.inversor.valor_usd), 'Histórico'],
        ])
    if r.deudor is not None:
        filas.extend([
            ['Costo de deuda', 'Costo anualizado', _fmt_pct(r.deudor.valor), 'Histórico'],
            ['Costo de deuda', 'Costo ajustado por inflación', _fmt_pct(r.deudor.rendimiento_real), 'Histórico con supuesto'],
            ['Costo de deuda', 'Costo anualizado USD', _fmt_pct(r.deudor.valor_usd), 'Histórico'],
        ])
    for escenario in e.resultados:
        filas.append([
            'Escenarios',
            f'Neto USD — {escenario.nombre}',
            _fmt_usd(escenario.neto_usd),
            'Escenario',
        ])
    return filas


def _markdown_reporte(reporte: ReportePersona) -> str:
    p = reporte.posicion
    plan = reporte.planificacion
    r = reporte.rendimiento
    lineas = [
        '# Reporte financiero',
        '',
        f'**Persona:** {reporte.nombre}',
        f'**Fecha de corte:** {reporte.fecha_corte:%d/%m/%Y}',
        f'**Horizonte:** {reporte.horizonte_meses} meses',
        '',
        '> Este reporte resume únicamente la información registrada en Préstamos Privados. No representa todo el patrimonio de la persona.',
        '',
        '## Posición conocida',
        '',
        f'- Capital invertido: **{_fmt_pesos(p.capital_invertido)}**',
        f'- Capital pendiente de deuda: **{_fmt_pesos(p.capital_deuda_pendiente)}**',
        f'- Posición neta de capital: **{_fmt_pesos(p.posicion_neta_capital)}**',
        f'- Cobros reales registrados: **{_fmt_pesos(p.cobros_reales)}**',
        f'- Pagos reales registrados: **{_fmt_pesos(p.pagos_reales)}**',
        '',
        '## Plan futuro',
        '',
        f'- Cobros futuros estimados: **{_fmt_pesos(plan.cobros_estimados_total)}**',
        f'- Pagos futuros estimados: **{_fmt_pesos(plan.pagos_estimados_total)}**',
        f'- Resultado futuro estimado: **{_fmt_pesos(plan.neto_estimado_total)}**',
        f'- Reserva de referencia: **{_fmt_pesos(plan.reserva_sugerida)}**',
        '',
        '## Rendimiento histórico',
        '',
    ]
    if r.inversor is not None:
        lineas.extend([
            f'- Rendimiento anualizado: **{_fmt_pct(r.inversor.valor)}**',
            f'- Rendimiento ajustado por inflación: **{_fmt_pct(r.inversor.rendimiento_real)}**',
            f'- Rendimiento anualizado USD: **{_fmt_pct(r.inversor.valor_usd)}**',
            f'- Movimientos reales utilizados: **{r.inversor.cantidad_flujos_reales}**',
        ])
    if r.deudor is not None:
        lineas.extend([
            f'- Costo anualizado: **{_fmt_pct(r.deudor.valor)}**',
            f'- Costo ajustado por inflación: **{_fmt_pct(r.deudor.rendimiento_real)}**',
            f'- Costo anualizado USD: **{_fmt_pct(r.deudor.valor_usd)}**',
            f'- Movimientos reales utilizados: **{r.deudor.cantidad_flujos_reales}**',
        ])
    if r.inversor is None and r.deudor is None:
        lineas.append('- Todavía no hay una posición con movimientos reales.')
    lineas.extend(['', '## Escenarios', ''])
    lineas.append('Los escenarios son comparaciones, no predicciones.')
    for escenario in reporte.escenarios.resultados:
        neto_usd = _fmt_usd(escenario.neto_usd)
        lineas.append(
            f'- **{escenario.nombre}** — inflación {_fmt_pct(escenario.inflacion_mensual)}, devaluación {_fmt_pct(escenario.devaluacion_mensual)}, neto nominal {_fmt_pesos(escenario.neto_nominal)}, neto real {_fmt_pesos(escenario.neto_real)}, neto USD {neto_usd}.'
        )
    lineas.extend([
        '',
        '## Supuestos y límites',
        '',
        f'- Inflación mensual utilizada para rendimiento real: **{_fmt_pct(reporte.inflacion_mensual_supuesto)}**.',
        '- Los datos futuros son estimaciones contractuales.',
        '- Los datos históricos se basan en movimientos reales registrados.',
        '- El reporte no incorpora sueldo, gastos, ahorros, bienes u otras deudas que la aplicación no conozca.',
        '- El reporte no constituye asesoramiento financiero.',
    ])
    return '\n'.join(lineas)