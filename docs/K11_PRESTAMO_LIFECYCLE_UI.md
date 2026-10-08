# K11 — Ciclo de vida de préstamos desde la UI

K11 completa la administración básica de un préstamo después del alta.

## Estados

La persistencia mantiene los estados:

BORRADOR, ACTIVO, EN_MORA, REFINANCIADO, CANCELADO, FINALIZADO y ANULADO.

La UI no puede realizar transiciones arbitrarias. El caso de uso central es
ServicioPrestamos.cambiar_estado().

## Transiciones

BORRADOR → ACTIVO, ANULADO

ACTIVO → EN_MORA, FINALIZADO, REFINANCIADO, CANCELADO, ANULADO

EN_MORA → ACTIVO, FINALIZADO, REFINANCIADO, CANCELADO, ANULADO

REFINANCIADO, CANCELADO, FINALIZADO y ANULADO son estados terminales para
esta etapa.

## Reglas

- FINALIZADO solo es válido cuando todas las cuotas de la versión vigente están en estado PAGADA o ANULADA.
- cancelar, refinanciar o anular exige motivo;
- una transición inexistente genera ErrorEstadoInvalido;
- una operación sin usuario válido es rechazada;
- cada transición genera una entrada de auditoría con estado anterior, estado nuevo, motivo y correlación.

## UI

La lista de préstamos permite consultar Activos, Finalizados, Cancelados,
Refinanciados y Todos.

El detalle muestra las transiciones permitidas y bloquea las que no cumplen
sus condiciones.

## Atomicidad

El cambio de estado y su auditoría se ejecutan dentro de una misma
transacción de aplicación.

## Fuera de alcance

K11 no implementa todavía refinanciación financiera, cálculo automático de
mora, anulación financiera de pagos ni autenticación/autorización de
operadores.
