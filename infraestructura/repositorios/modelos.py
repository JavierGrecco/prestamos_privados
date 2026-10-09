"""
Modelos de datos del sistema.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class Persona:
    id: int | None = None
    nombre: str = ""
    apellido: str = ""
    documento: str | None = None
    telefono: str | None = None
    email: str | None = None
    domicilio: str | None = None
    notas: str | None = None
    estado: str = "ACTIVO"
    creado_en: str | None = None
    actualizado_en: str | None = None

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()


@dataclass
class Prestamo:
    id: int | None = None
    numero: str = ""
    deudor_id: int | None = None
    moneda_contractual: str = "ARS"
    capital_original: Decimal = Decimal("0.00")
    plazo_meses: int = 0
    sistema: str = "FRANCES"
    convencion_dias: str = "MENSUAL"
    tc_inicial: Decimal | None = None
    fecha_inicio: date | None = None
    fecha_fin_estimada: date | None = None
    estado: str = "ACTIVO"
    destino: str | None = None
    descripcion: str | None = None
    creado_en: str | None = None
    actualizado_en: str | None = None


@dataclass
class Cuota:
    id: int | None = None
    version_id: int | None = None
    numero: int = 0
    fecha_vencimiento: date | None = None
    capital_inicial: Decimal = Decimal("0.00")
    interes: Decimal = Decimal("0.00")
    interes_carencia: Decimal = Decimal("0.00")
    interes_carencia_pendiente: Decimal = Decimal("0.00")
    capital: Decimal = Decimal("0.00")
    cuota: Decimal = Decimal("0.00")
    saldo: Decimal = Decimal("0.00")
    interes_pendiente: Decimal = Decimal("0.00")
    capital_pendiente: Decimal = Decimal("0.00")
    mora_pendiente: Decimal = Decimal("0.00")
    monto_pendiente: Decimal = Decimal("0.00")
    fue_mora: bool = False
    tuvo_pago_parcial: bool = False
    fue_recalculada: bool = False
    estado: str = "PENDIENTE"
    creado_en: str | None = None

    @property
    def total_pendiente(self) -> Decimal:
        return (
            self.interes_pendiente
            + self.capital_pendiente
            + self.mora_pendiente
        )

    @property
    def monto_total_a_pagar(self) -> Decimal:
        return self.cuota + self.total_pendiente


@dataclass
class Participacion:
    id: int | None = None
    prestamo_id: int | None = None
    inversor_id: int | None = None
    capital_aportado: Decimal = Decimal("0.00")
    moneda_aporte: str = "ARS"
    tc_aporte: Decimal | None = None
    capital_usd_ref: Decimal | None = None
    porcentaje: Decimal = Decimal("0.00")
    fecha_aporte: date | None = None
    estado: str = "ACTIVA"
    creado_en: str | None = None


@dataclass
class Pago:
    id: int | None = None
    prestamo_id: int | None = None
    fecha_real: date | None = None
    fecha_valor: date | None = None
    fecha_registro: str | None = None
    moneda_pago: str = "ARS"
    monto_moneda_pago: Decimal = Decimal("0.00")
    tc_aplicado: Decimal | None = None
    monto_moneda_contractual: Decimal = Decimal("0.00")
    monto_usd_ref: Decimal | None = None
    medio: str | None = None
    referencia: str | None = None
    nota: str | None = None
    estado: str = "VALIDA"
    motivo_anulacion: str | None = None
    creado_por: str | None = None
    tipo_pago: str = "CUOTA"
    monto_a_capital: Decimal = Decimal("0.00")
    intereses_ahorrados: Decimal = Decimal("0.00")
    interes_extra_generado: Decimal = Decimal("0.00")
    cuotas_restantes_antes: int = 0
    cuotas_restantes_despues: int = 0
    opcion_adelanto: str | None = None
    politica_pago_id: int | None = None


@dataclass
class Imputacion:
    id: int | None = None
    pago_id: int | None = None
    cuota_id: int | None = None
    concepto: str = ""
    monto: Decimal = Decimal("0.00")
    creado_en: str | None = None


@dataclass
class HistorialRecalculo:
    id: int | None = None
    prestamo_id: int | None = None
    pago_id: int | None = None
    tipo: str = ""
    fecha: date | None = None
    capital_antes: Decimal = Decimal("0.00")
    capital_despues: Decimal = Decimal("0.00")
    cuotas_antes: int = 0
    cuotas_despues: int = 0
    intereses_antes: Decimal = Decimal("0.00")
    intereses_despues: Decimal = Decimal("0.00")
    detalle_json: str | None = None
    creado_en: str | None = None
    cuota_objetivo_numero: int = 0


@dataclass
class MovimientoLedger:
    id: int | None = None
    entidad: str = ""
    entidad_id: int = 0
    tipo_movimiento: str = ""
    debe: Decimal = Decimal("0.00")
    haber: Decimal = Decimal("0.00")
    fecha: date | None = None
    metadata: str | None = None
    correlacion_id: str = ""
    creado_en: str | None = None


@dataclass
class TipoCambio:
    id: int | None = None
    fecha: date | None = None
    fuente: str = ""
    valor: Decimal = Decimal("0.00")
    es_manual: bool = False
    creado_por: str | None = None
    creado_en: str | None = None


@dataclass
class EntradaAuditoria:
    id: int | None = None
    fecha: str = ""
    usuario: str = ""
    operacion: str = ""
    entidad: str = ""
    entidad_id: int | None = None
    datos_anteriores: str | None = None
    datos_nuevos: str | None = None
    motivo: str | None = None
    correlacion_id: str = ""

@dataclass(frozen=True)
class GarantiaPrestamo:
    """Relación histórica de garantía personal asociada a un préstamo."""

    id: int
    prestamo_id: int
    garante_id: int
    alcance: str
    monto_maximo: Decimal | None
    moneda: str
    estado: str
    fecha_constitucion: date
    fecha_fin: date | None
    motivo_fin: str | None
    creado_por: str
    creado_en: str
    actualizado_en: str


@dataclass(frozen=True, slots=True)
class CondicionesCarenciaPersistidas:
    """Snapshot de condiciones de carencia almacenado sin edición in-place."""

    id: int
    prestamo_id: int
    version_tasa_id: int
    version_contrato: int
    tratamiento: str
    capital_original: Decimal
    tasa_anual: Decimal
    modalidad_tasa: str
    convencion_dias: str
    sistema: str
    meses_carencia: int
    fecha_desembolso: date
    fecha_fin_carencia: date
    fecha_primer_vencimiento: date
    plazo_amortizacion_meses: int
    interes_simple_referencia: Decimal
    interes_carencia_debido: Decimal
    interes_carencia_no_cobrado: Decimal
    snapshot_json: str
    snapshot_sha256: str
    creado_por: str
    creado_en: str

