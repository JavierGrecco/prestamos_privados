# I15 — Preflight V3 coherente y evidencia no destructiva

## Objetivo

Alinear todos los puntos de activación y readiness con un único baseline de schema y reducir el riesgo operativo al conservar evidencia de canary.

## Cambios

### Baseline único

El schema mínimo para activar V3 queda definido en:

~~~text
VERSION_MINIMA_SCHEMA_V3 = 13
~~~

El preflight usa ese valor por defecto, y la configuración persistente y el readiness reutilizan exactamente la misma constante.

Esto evita que una ejecución aislada del CLI pueda parecer apta con un schema más antiguo que el admitido por el gate de activación efectivo.

### Evidencia protegida

El precheck acepta:

~~~bash
python -m scripts.canary_precheck_motor_pago_v3 datos/prestamos.db \
  --output evidencia/canary-readiness.json
~~~

El archivo se escribe de forma atómica y, por defecto, un archivo existente no se reemplaza. Ante un nombre ya utilizado, el comando devuelve error operativo (`exit 1`) y conserva intacta la evidencia anterior.

La sobrescritura requiere una acción explícita:

~~~bash
python -m scripts.canary_precheck_motor_pago_v3 datos/prestamos.db \
  --output evidencia/canary-readiness.json \
  --force-output
~~~

`--force-output` debe reservarse para una nueva evidencia intencional o para un proceso que haya identificado de forma explícita que el artefacto anterior puede reemplazarse.

## Criterio operativo

1. generar un nuevo archivo de evidencia con nombre único o fecha/hora;
2. revisar el resultado y conservarlo;
3. no reemplazar evidencia histórica por conveniencia;
4. activar V3 solamente mediante el caso de uso persistente que vuelve a verificar el preflight.

## Seguridad

Estos cambios son de solo lectura sobre la base durante el precheck. No cambian el modo del motor ni ejecutan pagos.
