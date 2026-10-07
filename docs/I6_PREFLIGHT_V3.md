# I6 — Preflight objetivo para V3

## Objetivo

Convertir la preparación del cut-over en una decisión reproducible y explícita.

El servicio `PreflightMotorPagoV3` no cambia el modo del puente, no ejecuta pagos
y no escribe datos. Solo evalúa criterios sobre el estado actual.

## Criterios

- schema mínimo v012;
- auditoría de integridad V3 sin incidencias;
- mínimo configurable de ejecuciones SOMBRA;
- máximo configurable de divergencias;
- máximo configurable de errores;
- tasa mínima configurable de coincidencia.

## Valores conservadores por defecto

- 100 ejecuciones;
- 100% de coincidencia;
- 0 divergencias;
- 0 errores.

Estos valores no significan que el sistema actual ya cumpla el gate. Son el
umbral predeterminado que deberá cumplirse antes de una activación futura.

## Resultado

El resultado expone cada criterio por separado y una colección de motivos de
rechazo. Esto permite que una futura UI, CLI o pipeline de despliegue muestre
exactamente por qué V3 todavía no debe activarse.

## Límite

I6 no implementa todavía el feature flag ni el cut-over. La activación continúa
siendo una decisión posterior, reversible y basada en evidencia.
