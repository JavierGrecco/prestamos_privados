# Motor de Pagos V3-F.1 — Command de Registro

Separa la intención operacional de registrar un pago de la decisión financiera `PlanPago`.

`RegistrarPagoCommand` no calcula mora, interés, capital ni accede a SQLite.

Incluye `idempotency_key` y `revision_prestamo` para que la frontera de aplicación pueda implementar posteriormente deduplicación y control optimista, sin contaminar el dominio financiero.
