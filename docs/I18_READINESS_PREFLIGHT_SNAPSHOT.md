# I18 — Readiness basado en una única evaluación de preflight

El readiness de canary consume ahora la evidencia capturada por `PreflightMotorPagoV3` en la misma evaluación.

Antes, el servicio ejecutaba de forma independiente:

1. auditoría de integridad;
2. preflight, que volvía a auditar integridad y métricas;
3. una segunda lectura de métricas.

Eso podía generar resultados de dos instantes distintos si la base cambiaba entre consultas.

Ahora `ResultadoPreflightV3` conserva una fotografía de:

- schema actual;
- integridad;
- ejecuciones SOMBRA;
- tasa de coincidencia;
- divergencias;
- errores.

El readiness reutiliza esa evidencia y evita repetir las consultas. Los tests verifican que integridad y métricas se leen una sola vez durante la evaluación.

El cambio es de observabilidad/consistencia; no modifica reglas financieras ni escribe en la base.
