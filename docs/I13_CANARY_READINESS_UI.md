# Readiness de canary V3 en la UI

La pantalla **Motor de Pagos V3** muestra ahora el mismo resultado de readiness
que utiliza el precheck operativo.

Esto evita que la UI y el CLI puedan mostrar criterios diferentes.

## Controles

- integridad V3;
- preflight;
- modo actual y revisión;
- cantidad de ejecuciones SOMBRA;
- tasa de coincidencia;
- divergencias;
- errores.

## Resultado

El estado **Listo para canary** solo aparece cuando:

1. la integridad V3 es correcta;
2. todos los criterios de preflight están aprobados;
3. el modo persistido todavía es LEGACY o SOMBRA.

La pantalla no activa V3 automáticamente. La activación continúa siendo una
decisión explícita mediante el cambio persistente de modo, con motivo y
auditoría.
