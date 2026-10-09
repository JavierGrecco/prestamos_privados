"""
Motor financiero del sistema de préstamos privados.

Este paquete no sabe nada de base de datos, ni de interfaz gráfica,
ni de HTTP. Solo sabe de números. Eso lo hace testeable de forma
aislada y reutilizable en cualquier capa superior.
"""
from .tipos import (
    money, rate,
    SistemaAmortizacion, ModalidadTasa, ConvencionDias,
    ConceptoImputacion, ORDEN_DEFAULT_IMPUTACION,
)
from .excepciones import (
    ErrorPrestamos, ErrorValidacion, ErrorCalculo, ErrorInvariante,
    ErrorCapitalInsuficiente, ErrorTasaFueraDeRango,
)
from .interes import tasa_mensual, interes_periodo
from .carencia import TramoInteresCarencia, ResultadoInteresCarencia, calcular_interes_carencia_simple
from .amortizacion import generar_tabla, cuota_francesa
from .imputacion import imputar_pago
from .mora import calcular_mora
from .xirr import xirr
from .escenarios import (
    EscenarioMacro, ResultadoEscenario,
    simular_escenario, comparar_escenarios,
    escenarios_predefinidos_argentina,
)
from .analisis_cambiario import (
    calcular_rendimiento_usd, calcular_rendimiento_real,
    calcular_costo_equivalente_usd, calcular_tc_paridad,
)
from .licuacion import (
    factor_inflacion_acumulada, valor_real,
    proyectar_licuacion, calcular_tasa_real,
)
from .estrategias import (
    TipoAjuste, AjusteProgramado, EstrategiaRendimiento,
    calcular_tasa_efectiva_estrategia,
    estrategias_predefinidas_argentina,
)
from .simulador import simular_plazo, comparar_plazos, simular_tasas
from .motor_pagos_v3 import PlanPagoV3, calcular_plan_pago
from .politica_pago import PoliticaImputacionPago, EstrategiaObligacionesPago, BaseMoraPago
from .plan_pago import PlanPagoLegacy

__all__ = [
    # Tipos
    "money", "rate",
    "SistemaAmortizacion", "ModalidadTasa", "ConvencionDias",
    "ConceptoImputacion", "ORDEN_DEFAULT_IMPUTACION",
    # Excepciones
    "ErrorPrestamos", "ErrorValidacion", "ErrorCalculo", "ErrorInvariante",
    "ErrorCapitalInsuficiente", "ErrorTasaFueraDeRango",
    # Motor
    "tasa_mensual", "interes_periodo",
    "TramoInteresCarencia", "ResultadoInteresCarencia", "calcular_interes_carencia_simple",
    "generar_tabla", "cuota_francesa",
    "imputar_pago", "calcular_mora", "xirr",
    # Escenarios
    "EscenarioMacro", "ResultadoEscenario",
    "simular_escenario", "comparar_escenarios",
    "escenarios_predefinidos_argentina",
    # Análisis cambiario
    "calcular_rendimiento_usd", "calcular_rendimiento_real",
    "calcular_costo_equivalente_usd", "calcular_tc_paridad",
    # Licuación
    "factor_inflacion_acumulada", "valor_real",
    "proyectar_licuacion", "calcular_tasa_real",
    # Estrategias
    "TipoAjuste", "AjusteProgramado", "EstrategiaRendimiento",
    "calcular_tasa_efectiva_estrategia",
    "estrategias_predefinidas_argentina",
    # Simulador
    "simular_plazo", "comparar_plazos", "simular_tasas",
    # Contratos de planes de pago
    "PlanPagoV3", "calcular_plan_pago", "PlanPagoLegacy",
    "PoliticaImputacionPago", "EstrategiaObligacionesPago", "BaseMoraPago",
]