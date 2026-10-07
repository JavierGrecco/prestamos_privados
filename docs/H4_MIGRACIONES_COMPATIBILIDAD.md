# H4 — Compatibilidad de migraciones sobre bases existentes

## Objetivo

Verificar que una base que ya contiene información financiera puede evolucionar
a la versión actual sin cambiar su resultado económico.

## Escenario

La prueba construye una base hasta **v009**, crea sobre ella un préstamo real,
participaciones y un pago ejecutado por Legacy. Después toma un snapshot de las
tablas económicas y aplica **v010 — devengamientos V3**.

El snapshot se compara antes y después de la migración. La nueva tabla
`devengamientos`, sus índices y sus triggers se verifican como infraestructura
agregada, no como modificación de hechos financieros existentes.

## Qué protege

- personas y roles;
- préstamos y revisión;
- versiones de tasa;
- cuotas y saldos;
- participaciones;
- pagos;
- imputaciones;
- ledger;
- tipos de cambio;
- auditoría.

## Idempotencia

También se verifica que, una vez registrada v010, una nueva ejecución completa
del gestor no tenga migraciones pendientes y no modifique la información
económica.

## Limitación deliberada

El escenario actual valida v009 → v010. No pretende sustituir una batería
histórica con varias versiones reales de bases productivas. Esa matriz puede
incorporarse posteriormente con fixtures de bases representativas anonimizadas.

## Resultado esperado

Las migraciones deben ser aditivas respecto de la economía histórica y nunca
recalcular saldos existentes por accidente.
