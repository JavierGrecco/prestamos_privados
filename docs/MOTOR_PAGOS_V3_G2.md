# Motor de Pagos V3 — G2: composición de devengamientos + PlanPago

G2 conecta dos piezas que ya estaban separadas:

`Estado vigente -> devengamientos nuevos -> calcular_plan_pago()`

La composición continúa siendo pura desde el punto de vista financiero: no
abre transacciones, no actualiza cuotas y no persiste eventos.

## Regla económica incorporada

La política G1 genera interés adicional únicamente sobre el **capital que
realmente continúa pendiente**. Si existe un devengamiento anterior para esa
cuota, el nuevo período comienza en su `fecha_hasta`.

Esto permite que un pago parcial reduzca la base para el siguiente período y
evita volver a cobrar el intervalo ya devengado.

## Qué todavía NO hace

G2 no decide por sí mismo que todos los créditos tengan mora, no fija una tasa
legal/comercial de mora y no convierte automáticamente el interés francés
contractual en un interés adicional. Esas decisiones siguen perteneciendo a la
política explícita del crédito.

Tampoco persiste todavía los eventos generados junto con el pago.

## Siguiente paso

G3 debe conectar el repositorio de devengamientos con esta composición dentro
de la transacción de registro, persistiendo cada evento solo si el plan que lo
usa termina en COMMIT.
