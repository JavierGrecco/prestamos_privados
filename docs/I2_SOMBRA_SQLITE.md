# I2 — SOMBRA real sobre SQLite

## Objetivo

Llevar el contrato I1 a una ejecución real sobre la base SQLite de la aplicación.

La operación mantiene a Legacy como motor efectivo y utiliza V3 únicamente como
cálculo de comparación.

## Flujo

```text
RegistrarPagoCommand
        ↓
capturar EstadoRegistroPagoV3
        ↓
Legacy registra y persiste
        ↓
V3 calcula PlanPago desde el snapshot
        ↓
comparador Legacy vs PlanPago
        ↓
ResultadoSombra
```

El planificador V3 no consulta nuevamente cuotas después de Legacy y no llama a
ninguna operación de persistencia V3.

## Alcance inicial

El primer escenario cubre el pago ordinario:

- monto;
- tipo de pago;
- imputaciones por cuota y concepto;
- saldos finales de las obligaciones afectadas;
- estado final de esas obligaciones.

No se incluyen todavía devengamientos nuevos, distribución a inversores ni
recalculos RAI/RNI dentro de la comparación sombra. Esas extensiones quedan para
una segunda fase después de estabilizar esta ruta.

## Garantía de no-escritura

La integración verifica que después de una ejecución SOMBRA:

- existe el pago Legacy;
- no existe un pago con `motor_version` V3;
- no se generan devengamientos V3;
- el resultado efectivo continúa siendo el pago Legacy.

## Errores

Un fallo del cálculo V3 queda como `error_sombra` y no invalida el pago Legacy.
Esto permite utilizar SOMBRA durante la transición sin convertir la observación
en un nuevo punto único de falla.

## Criterio de salida

I2 queda listo cuando el flujo SQLite sea reproducible, el plan sombra utilice
el snapshot previo y CI quede verde en Python 3.11–3.14.
