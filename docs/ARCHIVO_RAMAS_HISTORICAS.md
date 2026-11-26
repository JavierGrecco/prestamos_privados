# Archivo de ramas históricas — noviembre de 2026

## Decisión

El repositorio mantiene `main` como única línea estable de desarrollo. Las 14 ramas antiguas no deben seguir figurando como si fueran trabajo activo, pero tampoco corresponde eliminar sus commits exclusivos sin preservar una vía de recuperación.

Se creó una única referencia de archivo:

- **Rama:** `archive/legacy-branches-2026-11`
- **Commit de anclaje:** `0f22a23d4e2dceed7b1a9020d79bc8d75925f378`
- **Árbol Git:** `0ff8027f4f23b0670cb2ef76c868a093e0081ef8`
- **Base estable original:** `1192e5d3dca1515ecd0b1baf5ba8284d2e9d4908`

El commit de anclaje tiene 15 padres: el `main` de base y los 14 HEAD históricos. Su árbol es exactamente el mismo árbol que el `main` de base. Esto conserva los objetos y todas las historias como alcanzables desde la referencia de archivo, **sin combinar sus cambios de código en `main` ni declarar que esas funcionalidades fueron integradas**.

El inventario machine-readable está en [ARCHIVO_RAMAS_HISTORICAS_2026-11.json](ARCHIVO_RAMAS_HISTORICAS_2026-11.json). Cada elemento fija el nombre, el SHA exacto, la categoría y la decisión de conservarlo.

## Qué se retira y qué se conserva

La PR #388 incorpora una segunda fase al workflow `branch housekeeping`. En el siguiente push a `main`, el workflow:

1. Lee el manifiesto versionado desde el propio commit de `main`.
2. Comprueba que la rama de archivo apunta al SHA esperado, que el commit conserva el árbol original y que sus 15 padres incluyen el `main` de base y todos los 14 HEAD históricos.
3. Para cada rama, exige que siga apuntando al SHA exacto inventariado, que no esté protegida ni tenga PR abierta y que GitHub confirme que ese commit es ancestro del commit de archivo.
4. Solo entonces elimina la referencia individual. Si cambia el SHA, falta una prueba, hay un error de API o la rama está protegida/en uso, la conserva y deja advertencia.

El resultado esperado luego de completar esa ejecución es **dos referencias**: `main` y la rama de archivo. La verificación final se hace consultando el listado de ramas de GitHub y el resultado del workflow; no se considera finalizado por el solo hecho de fusionar la PR.

La rama de archivo es de solo lectura por convención: no se abre trabajo ni PR sobre ella. El nuevo desarrollo siempre parte del `main` actualizado en una rama temporal.

## Cómo recuperar una rama archivada

Para inspeccionar un commit histórico sin crear una línea activa:

```bash
git fetch origin archive/legacy-branches-2026-11
git switch --detach <SHA>
```

Para recrear una rama local de inspección:

```bash
git branch <nombre-original> <SHA>
```

Los nombres y SHA exactos están en el manifiesto JSON. Para rescatar una mejora, no se continúa desarrollando sobre el snapshot viejo: se crea una nueva rama desde `main` y se adapta o cherry-pickea selectivamente el cambio luego de revisar su compatibilidad, pruebas, permisos, arquitectura y estado del dominio.

## Clasificación técnica

| Rama histórica | Decisión |
|---|---|
| `chore/security-automation` | Superseded by the current unified security workflow, Dependabot configuration and expanded SECURITY.md in main. |
| `docs/update-mvp-status-after-pr237-20261010` | Historical documentation snapshot; current product, MVP and technical status documents have moved forward in main. |
| `feat/benchmark-cagr-freshness-20261010` | Historical benchmark/UI work. The current domain benchmark model evolved; preserve this older simulator page and tests only as a recovery reference. |
| `feat/redisenio-visual-oscuro-d4` | Older D4 visual redesign and navigation snapshot; main has later session, accessibility and UI evolution. Retain as visual history, not a merge candidate. |
| `feature/i1-sombra-snapshot` | Snapshot-based shadow implementation is superseded by the evolved main implementation and newer tests; do not enable V3 cut-over from this archived state. |
| `feature/k16-ui-exports-v2` | CSV exports are already present in main with a newer composition/ports design, tests and UI integrations. |
| `feature/l1-2-validar-evidencia-canary` | Contains a unique historical evidence validator/CLI not present in main; preserve for possible adaptation, but its schema/readiness assumptions are old and require review against v026 and issue #145. |
| `feature/m5-rendimiento-operaciones` | Contains a unique per-operation XIRR/read-model proposal, but the application query imports infrastructure directly; preserve for refactoring, not direct integration. |
| `feature/m6-reporte-financiero-persona` | Contains a consolidated personal report UI/read model not identical to main; the application layer depends on infrastructure, so retain only as a redesign reference. |
| `feature/ui-rendimiento-objetivo-usd` | Unique USD-denominated replenishment UI component; domain simulation exists in main but this screen is absent and lacked focused tests. Preserve for a future tested adaptation. |
| `fix/ui-sqlite-connection-lifecycle` | Older direct-DB/cache lifecycle is superseded by session-scoped UI resources, explicit DB-opening composition and current isolation tests. |
| `refactor/auditoria-read-port` | Older audit read-port DTO/adapter has been superseded by the current EntradaAuditoria contract and composition; preserve as architectural history. |
| `refactor/historial-pagos-read-port` | The public payment-history port is already present in main (same blob); the SQLite read model and composition evolved later in main. |
| `refactor/ui-alta-prestamo-servicio-personas-20261015` | The public person-service composition is already used by the current loan-onboarding screen; retain the old branch and tests only as recovery history. |

## Política posterior

- `main`: única rama estable y base obligatoria para cambios.
- `archive/legacy-branches-2026-11`: único anclaje de recuperación histórica; no es una rama de desarrollo.
- Trabajo temporal: una rama activa y una PR dirigida a `main`; squash merge y limpieza automática.
- No se hacen merges masivos ni cherry-picks sin evaluación y pruebas actuales.
- La protección administrativa de `main` y los checks requeridos siguen pendientes de configuración en el issue #157; el housekeeping no sustituye esa gobernanza.

Esta consolidación limpia las referencias visibles, no borra el trabajo histórico ni convierte el MVP en una versión lista para producción.
