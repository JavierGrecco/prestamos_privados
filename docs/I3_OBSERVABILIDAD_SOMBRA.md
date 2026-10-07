# I3 — Persistencia auditable de SOMBRA

## Objetivo

Registrar como evidencia histórica cada divergencia o error detectado durante
la ejecución sombra de V3.

## Modelo

La tabla `observaciones_sombra_v3` es append-only y conserva:

- préstamo;
- pago Legacy asociado;
- fingerprint;
- tipo de observación;
- resumen;
- detalle estructurado;
- correlación de ledger cuando existe;
- versión del motor;
- timestamp.

## Tipos

`DIVERGENCIA` representa una diferencia entre Legacy y V3 que debe clasificarse.

`ERROR_SOMBRA` representa una falla del cálculo, comparación u otra etapa de
observación de V3.

## Regla de no bloqueo

La observación ocurre después de la ejecución efectiva de Legacy. Si el cálculo,
comparador o persistencia de la observación falla, el resultado Legacy se
mantiene.

Una falla del observer queda expuesta como `error_sombra` para que pueda ser
diagnosticada sin convertir SOMBRA en una dependencia crítica del pago.

## Inmutabilidad

Las observaciones no se actualizan ni se eliminan. Una corrección o resolución
futura debe registrarse como un nuevo hecho, manteniendo la trazabilidad.

## Próximo paso

I4 puede construir métricas y consultas de adopción sobre esta tabla, por
ejemplo cantidad de divergencias por préstamo, tipo y fingerprint, sin tocar
el motor financiero.
