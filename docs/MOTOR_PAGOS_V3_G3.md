# Motor de Pagos V3 — G3: registro con devengamientos atómico

G3 conecta la composición de G2 con la persistencia SQLite de F3.1.

Flujo:

`BEGIN IMMEDIATE -> idempotencia -> snapshot -> últimos cortes ->
devengamientos nuevos -> PlanPago -> persistir eventos usados + pago + cuotas +
ledger + auditoría -> COMMIT`

Los eventos de devengamiento y el pago quedan en la misma transacción. Si falla
el ledger, la escritura del devengamiento también vuelve atrás.

## Decisión deliberada

G3 persiste solamente los devengamientos correspondientes a obligaciones que
forman parte del `PlanPago` del pago. No convierte el registro de un pago en un
proceso global de devengamiento de toda la cartera. Ese proceso general podrá
existir luego como una operación de accrual independiente.

## Qué demuestra

- idempotencia no duplica eventos;
- un segundo pago el mismo día no redevenga el intervalo ya registrado;
- el período siguiente comienza en el último corte;
- la base usa el capital materializado vigente;
- rollback elimina en conjunto pago, eventos y avance de revisión;
- eventos de cuotas que quedaron fuera del waterfall del pago no se persisten
  dentro de esta operación.

## No habilitado todavía

G3 sigue sin activar RAI/RNI, mora automática, capitalización de intereses ni
reemplazo del servicio legacy. La tasa de interés adicional se recibe como
política explícita al construir el caso de uso.
