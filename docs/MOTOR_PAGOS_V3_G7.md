# Motor de Pagos V3 — G7: read model y One Shot

## Alcance

Esta etapa es exclusivamente de lectura. No modifica pagos, cuotas, devengamientos ni ledger.

### Read model auditable

Expone:
- pago y datos contractuales
- imputaciones por cuota/concepto/monto/origen
- movimientos ledger vinculados al pago
- auditoría vinculada
- `plan_json`
- reconciliación de dinero, ledger y distribución a inversores

Antes de devolver el modelo verifica:
- suma de imputaciones == monto del pago
- ledger de pago y préstamo reconcilia el monto
- distribución de inversores reconcilia cuando existe
- `plan_hash` == SHA-256 de `plan_json`
- no hay correlaciones de ledger incompatibles
- auditoría comparte la correlación del ledger

### One Shot

`PagoOneShotV3` es una proyección preparada para UI/reportes. Resume capital,
interés, mora, prepago, ahorro de intereses, cuotas restantes, distribución e
integridad, sin recalcular el préstamo.

## Tests

12 tests del read model + One Shot.
