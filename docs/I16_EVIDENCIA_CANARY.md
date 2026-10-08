# I16 — Evidencia de canary auto-descriptiva y publicación robusta

## Objetivo

Hacer que el artefacto de evidencia sea interpretable aun meses después de la ejecución y reducir el riesgo de corrupción o colisión de archivos temporales.

## Contrato del artefacto

El JSON incluye:

- `evidence_format_version`: versión del formato de evidencia;
- `evaluator`: nombre del evaluador que produjo el informe;
- `evaluated_at`: timestamp UTC;
- `database`: ruta absoluta de la base evaluada;
- `politica`: schema mínimo y umbrales usados en esa ejecución;
- resultado de readiness, modo persistido, evidencia SOMBRA y motivos de rechazo.

Guardar los umbrales dentro del propio artefacto evita tener que reconstruir posteriormente qué significaba un `listo_para_canary=true`.

## Publicación

El archivo se genera en la misma carpeta de destino con un nombre temporal único, se vacía y sincroniza, y recién después se publica mediante reemplazo atómico.

Por defecto los archivos existentes siguen protegidos. `--force-output` mantiene la sustitución como una acción explícita.

## Alcance

Este cambio no altera reglas financieras, no ejecuta pagos y no modifica el modo del Motor de Pagos.