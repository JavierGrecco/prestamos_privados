# Motor de Pagos V3-E — Simulación paralela

## Objetivo

Crear una ruta de simulación que consuma directamente `PlanPago` del Motor V3 sin cambiar todavía la API pública ni el registro real.

## Flujo

`cuotas materializadas -> snapshot V3 -> calcular_plan_pago() -> PlanPago`

La simulación no modifica objetos de entrada ni la base de datos.

## Alcance

V3-E integra únicamente los saldos materializados de las cuotas. No agrega todavía el cálculo temporal de mora/interés adicional desde V3-C/D. Por eso no debe reemplazar aún la simulación productiva existente.

## Ventaja

Permite comparar gradualmente el comportamiento del motor nuevo contra el camino anterior, particularmente en:

- pagos parciales;
- complementos;
- pagos multi-cuota;
- excedentes;
- trazabilidad por cuota y concepto;
- determinismo.

## Siguiente paso

V3-F incorporará el adaptador temporal V3-B/C/D al contexto de simulación y después podremos exigir equivalencia explícita entre la simulación nueva y el registro real.
