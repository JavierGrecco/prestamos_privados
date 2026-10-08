"""Tests del contrato público de PlanPago durante J1.

La compatibilidad histórica se conserva, pero los nombres explícitos indican
qué resultado pertenece al legado y cuál es el resultado canónico V3.
"""
from dominio import PlanPagoLegacy, PlanPagoV3, calcular_plan_pago
from dominio.motor_pagos_v3 import PlanPago as PlanPagoInternoV3
from dominio.plan_pago import PlanPago as PlanPagoInternoLegacy


def test_plan_pago_v3_tiene_nombre_publico_estable():
    assert PlanPagoV3 is PlanPagoInternoV3
    assert callable(calcular_plan_pago)


def test_plan_pago_legacy_mantiene_compatibilidad_de_import():
    assert PlanPagoLegacy is PlanPagoInternoLegacy


def test_los_contratos_legacy_y_v3_son_explicitos_y_distintos():
    assert PlanPagoLegacy is not PlanPagoV3
