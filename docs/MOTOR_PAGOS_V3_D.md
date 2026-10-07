# Motor de Pagos V3-D — Trayectoria de capital real

## Objetivo

Construir, en memoria y de forma determinista, la trayectoria del capital realmente pendiente a partir de reducciones de capital efectivamente ocurridas.

## Regla temporal

Los eventos son efectivos desde su `fecha_valor`. Los cálculos sobre un período usan intervalos `[fecha_desde, fecha_hasta)`.

- eventos anteriores al período: se incorporan al punto inicial;
- eventos en `fecha_desde`: ya impactan el punto inicial;
- eventos dentro del período: generan nuevos puntos;
- eventos en `fecha_hasta`: quedan fuera de ese período.

## Por qué existe esta pieza

Un cronograma francés describe el capital que debería quedar si se cumplen los pagos previstos. La trayectoria real describe cuánto capital permanece realmente pendiente después de las aplicaciones de capital que efectivamente ocurrieron.

V3-D no calcula por sí mismo el `interés adicional`. Entrega la trayectoria real a V3-C.

## Flujo

`PlanPago -> aplicaciones CAPITAL -> EventoReduccionCapital -> TrayectoriaCapitalReal -> V3-C`

La capa de aplicación puede agregar la referencia real del pago cuando el evento proviene de un pago persistido.

## Deliberadamente fuera de V3-D

- SQLite y repositorios.
- `registrar_pago()`.
- idempotencia y concurrencia.
- anulación/contra-eventos.
- RAI/RNI.
- cambios del cronograma contractual.

## Invariantes

- capital real nunca negativo;
- ninguna reducción supera el capital disponible;
- la trayectoria comienza exactamente en `fecha_desde`;
- los puntos están estrictamente ordenados;
- el orden de entrada de eventos no cambia el resultado;
- las aplicaciones de interés/mora no reducen capital real.
