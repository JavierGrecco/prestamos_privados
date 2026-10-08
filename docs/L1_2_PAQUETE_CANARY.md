# L1.2 — Paquete reproducible de decisión de canary

## Propósito

L1.2 reúne en una única evidencia los elementos que deben revisarse antes de un
canary:

1. base SQLite evaluada;
2. backup verificable;
3. readiness V3 recién calculado;
4. operador declarado;
5. motivo de revisión.

## Regla

El paquete no activa V3, no cambia la configuración, no ejecuta pagos y no
modifica los hechos financieros.

Solo responde:

> ¿Existe evidencia suficiente para que una persona responsable revise la decisión de canary?

## Datos incluidos

- formato de evidencia;
- evaluador;
- timestamp UTC;
- ruta de la base;
- ruta del backup;
- SHA-256 y tamaño del backup;
- resultado de integridad del backup;
- readiness V3;
- modo actual y revisión;
- métricas SOMBRA;
- criterios y motivos de rechazo;
- operador declarado;
- motivo de revisión;
- `apto_para_revision_humana`.

## Validaciones

El paquete falla cuando la base o el backup no existen, el backup no pasa sus
controles, el readiness no está aprobado o faltan operador/motivo.

## Reproducibilidad

El readiness no se toma de un JSON antiguo: se vuelve a calcular sobre la base
actual.

## Artefactos

El CLI guarda el JSON mediante escritura atómica y no sobrescribe un archivo
existente salvo que se indique explícitamente `--force-output`.

## Uso

    python -m scripts.paquete_decision_canary_v3 datos/prestamos.db
      evidencia/backup/prestamos-canary.db
      --motivo "Revisión L1.2"
      --output evidencia/paquete-canary-2026-10-08.json

Código de salida: 0 = apto para revisión; 2 = no apto; 1 = error operativo.

## Límite

Un paquete apto no equivale a un canary ejecutado.

La ejecución sobre una base operativa autorizada, la primera operación V3, su
revisión y la decisión de continuidad siguen siendo actividades humanas y
controladas.

## Principio

> La automatización debe preparar la decisión, no tomarla por el operador.