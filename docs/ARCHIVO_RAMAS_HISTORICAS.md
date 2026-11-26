# Archivo de ramas históricas — noviembre de 2026

## Decisión

El repositorio mantiene `main` como única línea estable de desarrollo. Las 14 ramas antiguas no deben seguir figurando como si fueran trabajo activo, pero tampoco corresponde eliminar sus commits exclusivos sin preservar una vía de recuperación.

Se creó una única referencia de archivo:

- **Rama:** `archive/legacy-branches-2026-11`
- **Commit de anclaje final:** `29ab117ee384d9809a6944d0f9997d6207bb4c92`
- **Anclaje de las 14 ramas:** `0f22a23d4e2dceed7b1a9020d79bc8d75925f378`
- **Implementación de housekeeping preservada:** `0f02bdf317143fc8eab4da5cba732efc21798bba`
- **Árbol Git:** `0ff8027f4f23b0670cb2ef76c868a093e0081ef8`
- **Base estable original:** `1192e5d3dca1515ecd0b1baf5ba8284d2e9d4908`

El commit de anclaje final tiene dos padres: el anclaje previo de las 14 ramas y el commit que contiene la implementación de verificación/housekeeping. El anclaje previo tiene 15 padres: el `main` de base y los 14 HEAD históricos. El árbol del commit final y el del anclaje previo son exactamente iguales al árbol del `main` base. Así quedan preservados tanto los 14 historiales como el origen de la implementación de housekeeping, **sin combinar sus cambios de código en `main` ni declarar integradas las funcionalidades históricas**.

El inventario machine-readable está en [ARCHIVO_RAMAS_HISTORICAS_2026-11.json](ARCHIVO_RAMAS_HISTORICAS_2026-11.json). Cada elemento fija el nombre, el SHA exacto, la categoría y la decisión de conservarlo.

## Qué se retira y qué se conserva

La PR #388 incorpora una segunda fase al workflow `branch housekeeping`. En el siguiente push a `main`, el workflow:

1. Lee el manifiesto versionado desde el propio commit de `main`.
2. Comprueba que la rama de archivo apunta al SHA final esperado y que su commit de dos padres incluye el anclaje histórico anterior y la implementación de housekeeping.
3. Comprueba que el anclaje histórico anterior tiene 15 padres: el `main` de base y los 14 HEAD originales, y que el árbol de ambos commits coincide con el árbol base.
4. Para cada rama original, la implementación auxiliar y el alias M5, exige el SHA exacto, ausencia de protección/PR abierta y alcanzabilidad desde el anclaje final.
5. Solo entonces elimina la referencia individual. También retira la rama auxiliar de housekeeping y el alias temporal de M5, cuyos commits están preservados en el anclaje o duplican un HEAD ya archivado. Si cambia el SHA, falta una prueba, hay un error de API o la rama está protegida/en uso, la conserva y deja advertencia.

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
| `chore/security-automation` | El flujo actual ya incluye CodeQL, Dependabot, `pip-audit` y SECURITY.md. Dependency Review sigue pendiente de Dependency Graph (#389). |
| `docs/update-mvp-status-after-pr237-20261010` | Snapshot documental de octubre superado por el estado y roadmap posteriores. |
| `feat/benchmark-cagr-freshness-20261010` | El control de frescura ya está en main; se preserva la pantalla antigua como referencia. La prueba E2E útil se recupera en la PR actual. |
| `feat/redisenio-visual-oscuro-d4` | Snapshot visual anterior; main evolucionó y la aceptación manual sigue pendiente en #177. No integrar como bloque. |
| `feature/i1-sombra-snapshot` | La implementación SOMBRA actual evolucionó con snapshot, aislamiento e idempotencia. No habilitar cut-over desde esta rama antigua. |
| `feature/k16-ui-exports-v2` | Las exportaciones CSV ya están integradas en main mediante servicios y puertos actuales. |
| `feature/l1-2-validar-evidencia-canary` | Conserva un validador/CLI histórico no integrado como tal; podría adaptarse luego de revisar su esquema y readiness contra v026 y #145. |
| `feature/m5-rendimiento-operaciones` | Propuesta útil de XIRR por operación, pero consulta histórica depende de infraestructura desde aplicación. Preservar para rediseñar en #388, no integrar directamente. |
| `feature/m6-reporte-financiero-persona` | La evolución actual del reporte personal se integró en #119. No reintroducir la versión antigua sin nueva evaluación. |
| `feature/ui-rendimiento-objetivo-usd` | Componente UI de reposición en USD no conectado; preservar como referencia para una futura adaptación probada. |
| `fix/ui-sqlite-connection-lifecycle` | Reemplazada por apertura/composición SQLite y aislamiento por sesión de #367/#369. |
| `refactor/auditoria-read-port` | Contrato y composición actuales de auditoría evolucionaron; preservar la versión anterior solo como historia arquitectónica. |
| `refactor/historial-pagos-read-port` | El puerto de historial de pagos y su composición evolucionaron en main; no integrar la versión anterior. |
| `refactor/ui-alta-prestamo-servicio-personas-20261015` | La pantalla ya usa el servicio público de personas; la guarda arquitectónica se recupera como prueba en la PR actual. |

## Política posterior

- `main`: única rama estable y base obligatoria para cambios.
- `archive/legacy-branches-2026-11`: único anclaje de recuperación histórica; no es una rama de desarrollo.
- Trabajo temporal: una rama activa y una PR dirigida a `main`; squash merge y limpieza automática.
- No se hacen merges masivos ni cherry-picks sin evaluación y pruebas actuales.
- La protección administrativa de `main` y los checks requeridos siguen pendientes de configuración en el issue #157; el housekeeping no sustituye esa gobernanza.

Esta consolidación limpia las referencias visibles, no borra el trabajo histórico ni convierte el MVP en una versión lista para producción.
