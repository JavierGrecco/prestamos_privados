# J1 — Consolidación de PlanPago

## Situación

El proyecto tiene dos resultados de planificación que pertenecen a etapas
distintas de la arquitectura:

- `dominio.plan_pago.PlanPago`: contrato histórico usado por la ruta anterior
  de simulación/planificación;
- `dominio.motor_pagos_v3.PlanPago`: resultado canónico del motor V3.

No son equivalentes estructuralmente y no debemos fingir que lo son.

## Cambio de J1

Se agregan nombres públicos explícitos:

- `dominio.PlanPagoLegacy`;
- `dominio.PlanPagoV3`;
- `dominio.calcular_plan_pago`.

Los nombres antiguos continúan funcionando para preservar compatibilidad.

## Política

A partir de este punto, el código nuevo que pertenezca al motor V3 debe usar
`PlanPagoV3` y `calcular_plan_pago`.

La API histórica puede seguir utilizando `PlanPagoLegacy` mientras se migra.

Esto permite retirar posteriormente el módulo histórico sin romper todo el
proyecto en un único cambio.

## Próximo paso

Identificar consumidores reales de `PlanPagoLegacy`, migrarlos uno a uno y
solo entonces evaluar la eliminación del módulo histórico.
