# I1 — SOMBRA sobre snapshot previo

## Contrato

El modo SOMBRA no debe comparar resultados calculados sobre estados diferentes.

La secuencia correcta es:

```
RegistrarPagoCommand
       ↓
snapshot inmutable del estado inicial
       ↓
Legacy efectivo
       ↓
V3 sombra sobre el snapshot inicial
       ↓
comparación
       ↓
observación
```

El servicio `EjecutorSombraPagoV3` encapsula este orden y el `PuenteMotorPagoV3` lo utiliza como camino real del modo `SOMBRA`. El planificador sombra recibe el snapshot explícitamente y no debe releer el estado después de la mutación de Legacy.

## Tolerancia a fallas

Una falla del cálculo V3 sombra o del comparador queda registrada como `error_sombra` y no reemplaza el resultado efectivo de Legacy.

Esto es intencional: el modo SOMBRA existe para observar la migración, no para introducir un nuevo punto de falla en producción.

## Límite

El PR formaliza el contrato en memoria y en el puente. La integración concreta con el repositorio SQLite, incluyendo cómo construir el snapshot financiero completo antes de Legacy, será el siguiente paso de implementación del cut-over.
