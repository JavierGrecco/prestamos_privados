# Motor de Pagos V3 — G4 + G5

## Alcance

Esta entrega se instala **después de F3.1 + G1 + G2 + G3**.

### G4
- Distribución determinista del cobro entre participaciones activas.
- Método de resto mayor a centavos, con desempate por `inversor_id`.
- Ledger de distribución con la misma correlación del pago.
- Auditoría de distribución.
- Atomicidad: si la distribución falla, el pago y sus movimientos anteriores revierten.
- Corrección del horizonte del waterfall: las cuotas futuras no se cobran por accidente.
- `cuotas_restantes_despues` se calcula sobre el cronograma activo completo.

### G5
- Política pura de RAI/RNI.
- RAI conserva cantidad y fechas futuras.
- RNI acorta el plazo usando las primeras fechas futuras necesarias.
- Las cuotas reemplazadas se conservan como `REESTRUCTURADA`; no se borran.
- Se registra `historial_recalculos` y auditoría.
- El excedente se convierte explícitamente en `PREPAGO` y requiere `RAI` o `RNI`.
- Idempotencia impide repetir reestructuraciones.

## Garantías

- Suma de imputaciones == pago recibido.
- Suma de distribución a inversores == pago recibido.
- No se modifican eventos históricos del pago.
- Todo el flujo ocurre dentro de una sola transacción de escritura.

## Tests de esta entrega

25 tests enfocados:
- 6 distribución
- 5 registro completo
- 3 horizonte
- 5 adelanto puro
- 6 integración RAI/RNI con SQLite
