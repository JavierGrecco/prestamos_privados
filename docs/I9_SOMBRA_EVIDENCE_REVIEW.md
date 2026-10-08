# I9 — Revisión operativa de evidencia SOMBRA V3

La pantalla **Motor de Pagos V3** ya permite revisar las incidencias
persistidas por la ejecución SOMBRA sin modificar los hechos financieros.

## Qué se observa

La revisión muestra:

- cantidad de ejecuciones SOMBRA;
- tasa de coincidencia;
- divergencias;
- errores de sombra;
- incidencias individuales;
- fingerprint;
- préstamo y pago Legacy relacionados;
- fecha, resumen y correlación.

## Filtros

Las incidencias pueden filtrarse por:

- todas;
- divergencias;
- errores de sombra.

También puede limitarse la consulta a un préstamo determinado cuando la
pantalla fue abierta desde un contexto específico.

## Seguridad

La consulta es de solo lectura.

No existe desde esta pantalla una acción para:

- borrar observaciones;
- modificar una divergencia;
- marcar artificialmente una incidencia como resuelta;
- activar V3.

Una divergencia solo desaparece del criterio de preflight cuando la evidencia
real acumulada cumple los umbrales configurados.

## Relación con cut-over

El preflight sigue siendo el gate formal para V3. I9 agrega la capacidad humana
de revisar el detalle de las incidencias antes de considerar un canary o
cut-over.

El sistema mantiene Legacy como autoridad efectiva hasta que el operador
decida explícitamente cambiar de modo y el preflight lo permita.
