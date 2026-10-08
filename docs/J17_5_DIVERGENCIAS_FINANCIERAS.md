# J17.5 — Resolución de divergencias financieras Legacy/V3

## Estado

J17.5 avanza sobre una separación importante: algunas diferencias observadas
eran falta de una política explícita y otra diferencia es una decisión de
waterfall que todavía no debe alterarse automáticamente.

## Mora contractual

V3 ahora puede recibir una política explícita de mora contractual.

La política de compatibilidad actual reproduce el comportamiento que utiliza
Legacy en la consulta de deuda:

- tasa anual: 50%;
- convención temporal: ACTUAL/365;
- base: importe contractual completo de la cuota;
- generación: primera obligación pendiente que ya venció;
- concepto: MORA;
- origen auditable: `MORA_CONTRACTUAL`.

El importe queda modelado como un `Devengamiento` y entra al mismo waterfall
que las demás obligaciones. Esto permite comparar y persistir el evento sin
hacer que la UI conozca la fórmula.

La regresión de J17.4 para el escenario de pago vencido confirma que la mora
Legacy y V3 coincide. La divergencia residual queda reducida a INTERÉS y
CAPITAL porque V3 también genera explícitamente interés sobre capital pendiente
después del vencimiento.

Esto último no se elimina para forzar igualdad con Legacy: el principio del
proyecto mantiene que capital que continúa pendiente puede devengar interés y
H1 exige decidir expresamente qué regla debe ser autoridad antes del cut-over.

## Waterfall después de un pago parcial

La segunda divergencia es distinta. V3 utiliza un waterfall:

1. procesa las obligaciones cronológicamente;
2. dentro de cada obligación aplica MORA → INTERÉS → CAPITAL;
3. continúa con la siguiente obligación solo cuando queda remanente del pago.

Legacy, en cambio, construye la deuda próxima agregando arrastres y luego
distribuye el pago sobre ese agregado.

Por eso, después de un pago parcial, la misma cantidad puede terminar con
distinta distribución entre INTERÉS y CAPITAL aunque el dinero total aplicado y
la deuda total sean iguales.

No se cambia el waterfall V3 en este trabajo. Ya existe una regresión pura que
considera intencional el comportamiento obligación-primero para un complemento
de pago parcial. Modificarlo únicamente para igualar Legacy podría alterar una
decisión ya expresada en el motor nuevo.

## Criterio de salida

La comparación debe distinguir:

- **equivalencia:** mismo resultado económico;
- **diferencia explicada:** representación o trazabilidad;
- **decisión pendiente:** dos reglas financieras válidas pero incompatibles;
- **defecto:** resultado que viola la política financiera aceptada.

La incorporación de mora contractual reduce una diferencia de implementación.
La elección definitiva entre interés incremental sobre capital vencido y el
waterfall Legacy queda separada como decisión financiera antes del cut-over.

## Seguridad de adopción

Esta evolución:

- no cambia el modo efectivo de producción;
- no activa V3;
- no elimina Legacy;
- mantiene conservación de dinero e invariantes del PlanPago;
- agrega evidencia reproducible para el canary posterior.
