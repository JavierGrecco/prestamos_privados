# I5 — Registro completo de ejecuciones SOMBRA

## Objetivo

Registrar todas las ejecuciones del modo SOMBRA, incluso cuando Legacy y V3 no presentan ninguna divergencia.

## Resultado

Cada ejecución queda clasificada como:

- `SIN_DIVERGENCIA`
- `DIVERGENCIA`
- `ERROR_SOMBRA`

## Por qué se separa de observaciones

La tabla `observaciones_sombra_v3` de I3 representa incidentes que requieren
atención.

La tabla `ejecuciones_sombra_v3` representa el universo completo de ejecuciones.
Esto permite calcular métricas honestas de coincidencia, divergencia y error.

## Datos registrados

- préstamo;
- pago Legacy;
- fingerprint;
- resultado;
- revisión del snapshot;
- resumen cuando corresponde;
- motor;
- timestamp.

## Regla de no bloqueo

El registro de una ejecución es observabilidad. Si el almacenamiento de la
ejecución falla, el resultado financiero efectivo de Legacy no se modifica ni se
revierte.

## Métricas habilitadas

Con I5, I4 puede calcular:

`tasa_coincidencia = ejecuciones_sin_divergencia / ejecuciones_sombra`

`tasa_divergencia = ejecuciones_con_divergencia / ejecuciones_sombra`

`tasa_error = ejecuciones_con_error / ejecuciones_sombra`

Cuando no existen ejecuciones, las tasas son `None` en lugar de inventar un
porcentaje.
