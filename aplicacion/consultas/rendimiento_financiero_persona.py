"""Read model de rendimiento financiero explicado para una persona.

Convierte las métricas financieras existentes en una lectura humana.
No recalcula XIRR ni rendimiento real: reutiliza los resultados del análisis
financiero y agrega contexto, evidencia y estado de disponibilidad.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aplicacion.consultas.analisis_financiero import ServicioAnalisisFinanciero
from infraestructura.db import BaseDatos
from infraestructura.repositorios import PersonaRepo

ZERO = Decimal('0.00')

ROL_TITULO = {
    'INVERSOR': 'Rendimiento de tu inversión',
    'DEUDOR': 'Costo de tu deuda',
}

ROL_EXPLICACION = {
    'INVERSOR': 'Mide cómo rindió el dinero que pusiste, usando los movimientos reales registrados.',
    'DEUDOR': 'Mide el costo anualizado de tu deuda, usando el desembolso y los pagos reales registrados.',
}

@dataclass(frozen=True)
class IndicadorRendimiento:
    rol: str
    nombre: str
    valor: Decimal | None
    valor_usd: Decimal | None
    rendimiento_real: Decimal | None
    estado: str
    explicacion: str
    cantidad_flujos_reales: int
    cantidad_flujos_negativos: int
    cantidad_flujos_positivos: int
    fecha_desde: date | None
    fecha_hasta: date | None
    inflacion_mensual_supuesto: Decimal

    @property
    def disponible(self) -> bool:
        return self.estado == 'DISPONIBLE'

    @property
    def tiene_usd(self) -> bool:
        return self.valor_usd is not None

    @property
    def evidencia_completa(self) -> bool:
        return self.cantidad_flujos_negativos > 0 and self.cantidad_flujos_positivos > 0

@dataclass(frozen=True)
class RendimientoFinancieroPersona:
    persona_id: int
    fecha_corte: date
    inflacion_mensual_supuesto: Decimal
    inversor: IndicadorRendimiento | None
    deudor: IndicadorRendimiento | None
    advertencias: tuple[str, ...]


class RendimientoFinancieroPersonaQuery:
    """Construye indicadores de rendimiento a partir de hechos reales."""

    def __init__(self, db: BaseDatos) -> None:
        self._personas = PersonaRepo(db)
        self._analisis = ServicioAnalisisFinanciero(db)

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        inflacion_mensual_supuesto: Decimal = Decimal('0.05'),
    ) -> RendimientoFinancieroPersona:
        if persona_id <= 0:
            raise ValueError('persona_id debe ser positivo')
        if self._personas.obtener(persona_id) is None:
            raise ValueError(f'La persona {persona_id} no existe')

        corte = fecha_corte or date.today()
        inflacion = Decimal(str(inflacion_mensual_supuesto))
        resultado = self._analisis.obtener(
            persona_id,
            fecha_corte=corte,
            inflacion_mensual_supuesto=inflacion,
        )

        reales = tuple(resultado.flujos_reales)
        return RendimientoFinancieroPersona(
            persona_id=persona_id,
            fecha_corte=corte,
            inflacion_mensual_supuesto=inflacion,
            inversor=_indicador(
                rol='inversor',
                flujos=reales,
                xirr=resultado.resumen.xirr_inversor,
                xirr_usd=resultado.resumen.xirr_inversor_usd,
                real=resultado.resumen.rendimiento_real_inversor,
                inflacion=inflacion,
            ),
            deudor=_indicador(
                rol='deudor',
                flujos=reales,
                xirr=resultado.resumen.xirr_deudor,
                xirr_usd=resultado.resumen.xirr_deudor_usd,
                real=resultado.resumen.rendimiento_real_deudor,
                inflacion=inflacion,
            ),
            advertencias=resultado.advertencias,
        )


class ServicioRendimientoFinancieroPersona:
    """Caso de uso de lectura para la vista de rendimiento."""

    def __init__(self, db: BaseDatos) -> None:
        self._query = RendimientoFinancieroPersonaQuery(db)

    def obtener(
        self,
        persona_id: int,
        *,
        fecha_corte: date | None = None,
        inflacion_mensual_supuesto: Decimal = Decimal('0.05'),
    ) -> RendimientoFinancieroPersona:
        return self._query.obtener(
            persona_id,
            fecha_corte=fecha_corte,
            inflacion_mensual_supuesto=inflacion_mensual_supuesto,
        )


def _indicador(
    *,
    rol: str,
    flujos,
    xirr: Decimal | None,
    xirr_usd: Decimal | None,
    real: Decimal | None,
    inflacion: Decimal,
) -> IndicadorRendimiento | None:
    if rol not in {'inversor', 'deudor'}:
        raise ValueError('rol de rendimiento inválido')

    propios = tuple(f for f in flujos if f.rol == rol)
    if not propios:
        return None

    negativos = sum(f.monto_ars < ZERO for f in propios)
    positivos = sum(f.monto_ars > ZERO for f in propios)
    fechas = [f.fecha for f in propios]

    if rol == 'inversor':
        nombre = 'Rendimiento anualizado'
        explicacion = ROL_EXPLICACION['INVERSOR']
    else:
        nombre = 'Costo anualizado'
        explicacion = ROL_EXPLICACION['DEUDOR']

    if xirr is None:
        estado = 'NO_DISPONIBLE'
        explicacion += ' Todavía no hay suficientes flujos reales con entradas y salidas para calcular una tasa anualizada.'
    else:
        estado = 'DISPONIBLE'

    return IndicadorRendimiento(
        rol=rol.upper(),
        nombre=nombre,
        valor=xirr,
        valor_usd=xirr_usd,
        rendimiento_real=real,
        estado=estado,
        explicacion=explicacion,
        cantidad_flujos_reales=len(propios),
        cantidad_flujos_negativos=negativos,
        cantidad_flujos_positivos=positivos,
        fecha_desde=min(fechas),
        fecha_hasta=max(fechas),
        inflacion_mensual_supuesto=inflacion,
    )