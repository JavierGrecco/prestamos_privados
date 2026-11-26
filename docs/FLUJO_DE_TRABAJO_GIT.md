# Flujo de trabajo Git

## Regla principal

`main` es la única rama de referencia estable. Todo cambio de código, pruebas y documentación debe terminar integrado en `main`; ninguna rama de trabajo es una línea de desarrollo permanente.

El repositorio debe mantener:
- **Una rama de trabajo activa** para el conjunto de cambios en curso.
- Una segunda rama solo cuando haya una corrección urgente e independiente que no pueda esperar.
- Ninguna cadena de ramas dependientes ni PR apiladas sobre otras ramas de trabajo.

## Ciclo normal

1. Actualizar `main` y crear una sola rama desde su último commit.
2. Concentrar en esa rama los cambios relacionados, aunque se hagan en varios commits.
3. Abrir una única PR dirigida a `main`. No abrir otra rama para cada ajuste pequeño ni crear una rama derivada de la PR anterior.
4. Ejecutar y revisar la matriz completa: pruebas Python 3.11–3.14, inventario de arquitectura, CodeQL, auditoría de dependencias y chequeos de diff.
5. Para cambios financieros, conservar además las pruebas de caracterización, atomicidad, idempotencia, concurrencia y rollback que correspondan. CI verde no reemplaza la aceptación funcional.
6. Integrar con *squash merge* cuando todos los controles estén aprobados.
7. Eliminar la rama integrada y volver a trabajar desde `main`.

## Qué no se integra

Una rama cerrada sin merge no se considera integrada por el solo hecho de que su PR esté cerrada. Antes de eliminarla, debe verificarse que:
- su PR declara explícitamente que fue sustituida por otra entrega integrada; o
- el cambio se recuperó y validó en una PR posterior.

Las ramas sin PR o con cambios únicos se conservan hasta decidir si se rescatan, se archivan o se descartan. No se deben borrar por antigüedad solamente.

## Limpieza de ramas

El workflow [Branch housekeeping](../.github/workflows/branch-housekeeping.yml):
- en cada actualización de `main`, identifica y elimina ramas cuyo nombre y SHA coinciden exactamente con una PR integrada;
- también elimina ramas de PR cerradas que declaran expresamente que fueron sustituidas por otra PR ya integrada;
- elimina ramas cuyo HEAD es antecesor de `main`: sus commits ya están contenidos en la rama estable y no agregan trabajo exclusivo;
- al cerrar una PR integrada, elimina también su rama de trabajo actual, siempre que no esté protegida ni sea utilizada por otra PR abierta;
- permite inventariar las ramas históricas en modo **DRY RUN**;
- la limpieza manual exige `dry_run=false` y la confirmación exacta `DELETE_MERGED_BRANCHES`;
- nunca elimina `main`, ramas protegidas ni ramas que sigan siendo utilizadas por una PR abierta;
- conserva ramas divergentes o con commits exclusivos, aunque sus PR estén cerradas.

Para ejecutar la primera limpieza: GitHub → Actions → **branch housekeeping** → Run workflow. Primero dejar `dry_run=true` y revisar el resumen. Solo después de revisar los nombres, repetir con `dry_run=false`, confirmación exacta y, si corresponde, `include_superseded=true`.

Las ramas sin evidencia de integración quedan fuera de la limpieza automática. Deben revisarse por separado.

### Dirección de la comparación de ancestralidad

Cuando el workflow compara `branch...main`, GitHub recibe la rama como `BASE` y `main` como `HEAD`. La API compara `BASE..HEAD`:

- `behind_by` cuenta commits que existen en la rama base y no en `main`; para borrar una rama por ancestralidad debe ser **cero**.
- El estado esperado es `ahead` (main contiene commits posteriores) o `identical`.
- `ahead_by === 0` no sirve para demostrar que la rama esté contenida en `main`; puede seleccionar el caso contrario.

La automatización también vuelve a consultar la referencia después de un error de borrado. Solo considera que la rama ya no existe si esa consulta devuelve 404; cualquier otro error se conserva como fallo real. La prueba `tests/test_branch_housekeeping_workflow.py` protege estas condiciones. La acción `actions/github-script` se mantiene en su runtime Node 24.


## Convención de nombres

Usar nombres cortos que describan el objetivo y una fecha cuando ayude:
- `fix/<problema>`
- `feat/<capacidad>`
- `refactor/<frontera>`
- `docs/<documento>`

No crear variantes `-v2`, `-v3` o sufijos de iteración para evitar cerrar y consolidar trabajo; continuar en la misma rama mientras la PR siga siendo la unidad de integración.

## Inventario inicial — 26/11/2026

La consulta de GitHub encontró **294 ramas remotas** y una sola PR abierta (#357). El cruce con las PR cerradas deja esta fotografía:

| Grupo | Cantidad | Tratamiento |
|---|---:|---|
| Ramas cuyo nombre y SHA coinciden con una PR integrada en `main` | 237 | Borrado automático seguro al actualizar `main` |
| Rama asociada a PR integrada, pero con SHA distinto | 1 | Preservar y revisar; puede contener commits posteriores |
| Ramas cuyo HEAD coincide con PR cerradas sin merge | 36 | 18 tienen sustitución explícita; 18 requieren revisión |
| Ramas sin PR cerrada asociada | 18 | 7 ya están contenidas en `main`; 11 están adelantadas o divergentes y se preservan para revisión |
| Rama estable `main` | 1 | Conservar siempre |
| Rama de la PR abierta #357 | 1 | Conservar hasta integrar; luego entra en la limpieza automática |

El número de PR cerradas no es igual al número de ramas: algunas ramas ya no existen y puede haber PR antiguas con más de una iteración. Para las PR integradas se exige coincidencia exacta entre nombre de rama y SHA del HEAD, para evitar borrar una rama que haya avanzado después de la integración. Para ramas sin esa coincidencia, solo se borran si el commit completo ya es antecesor de `main`; cualquier rama adelantada o divergente queda preservada. La comparación inicial identificó siete ramas huérfanas que ya están contenidas en `main` y once ramas que requieren revisión manual. Al integrar la PR #357, la limpieza debería eliminar como mínimo 238 ramas integradas exactas, 18 ramas con sustitución documentada y esas siete ramas ya contenidas; también eliminará otras ramas de PR cerradas cuyo HEAD resulte ser antecesor de `main`. El número final lo informará el resumen de GitHub Actions.

La primera ejecución manual debe ser un **DRY RUN**. El resumen real de GitHub Actions es la lista definitiva de candidatos; estas cifras son el inventario observado antes de ejecutar la limpieza.



## Resultado de limpieza — 26/11/2026

### Primera pasada completada

La PR [#357](https://github.com/JavierGrecco/prestamos_privados/pull/357) integró la política de ramas en `main` mediante el commit [`a6d948b`](https://github.com/JavierGrecco/prestamos_privados/commit/a6d948ba04beb3285ea593266acaa664ad2ccdb1).

El workflow [branch housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45869098250) terminó con éxito:
- **263 ramas eliminadas**.
- 1 referencia ya estaba ausente.
- **0 fallos** de borrado.
- De 294 ramas iniciales se pasó a **31**, contando `main`.
- Se eliminaron ramas con PR integrada, ramas expresamente sustituidas por otras integradas y ramas cuyo HEAD ya estaba contenido en `main`.
- La rama predeterminada `main` se conservó en el commit `a6d948b`.

El CI post-merge de la misma entrega aprobó Python 3.11, 3.12, 3.13 y 3.14, CodeQL y auditoría de dependencias:
- [Matriz de pruebas](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45869098158)
- [Seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45869098161)

### Segunda pasada identificada

Se actualizaron los cierres históricos de 15 PR para dejar constancia de que sus ramas fueron reemplazadas por entregas integradas. El siguiente push a `main` las hará elegibles para el mismo workflow, que vuelve a validar nombre y SHA antes de borrarlas.

Las 15 ramas que deberían conservarse después de esa segunda pasada —además de `main`— son:

| Rama | Motivo de preservación |
|---|---|
| `chore/security-automation` | Incluye una propuesta de Dependency Review que no se integró porque el Dependency Graph no estaba disponible. |
| `docs/update-mvp-status-after-pr237-20261010` | Documentación divergente con cambios propios; requiere revisión. |
| `feat/benchmark-cagr-freshness-20261010` | Cambios de simulador y pruebas E2E no demostrados como integrados. |
| `feat/redisenio-visual-oscuro-d4` | Evolución visual divergente; requiere comparación con el diseño actual. |
| `feature/i1-sombra-snapshot` | El HEAD de la rama no coincide con el HEAD de la PR integrada #12. |
| `feature/k16-ui-exports-v2` | Contiene cambios propios de exportación; no hay evidencia de integración completa. |
| `feature/l1-2-validar-evidencia-canary` | Validador de evidencia de canary no encontrado en `main`; requiere revisión. |
| `feature/m4-escenarios-planificacion-v2` | Contiene un cambio propio de escenarios y planificación. |
| `feature/m5-rendimiento-operaciones` | Contiene read model y pantalla de rendimiento no demostrados como integrados. |
| `feature/m6-reporte-financiero-persona` | PR #120 cerrada sin merge; reporte financiero personal no encontrado en `main`. |
| `feature/ui-rendimiento-objetivo-usd` | Componente USD propio no demostrado como integrado. |
| `fix/ui-sqlite-connection-lifecycle` | Cambios propios en ciclo de conexión y pruebas; requiere revisión. |
| `refactor/auditoria-read-port` | Puerto y adaptador de auditoría con cambios propios; requiere revisión. |
| `refactor/historial-pagos-read-port` | Rama divergente de la versión integrada #287 y contiene cambios adicionales en consultas/reportes; no se descarta. |
| `refactor/ui-alta-prestamo-servicio-personas-20261015` | Cambios y pruebas de composición del alta que requieren comparación funcional. |

Esta lista es un inventario de **trabajo histórico preservado**, no 15 ramas activas. Ninguna tiene una PR abierta. No se integrarán en bloque: cada una se rescatará, se sustituirá o se descartará con evidencia propia.

### Estado operativo del repositorio

- `main` es la única rama estable.
- Una sola rama de trabajo y una sola PR abierta como máximo.
- Las ramas preservadas no se usan como base de nuevas ramas.
- Antes de trabajar en una de ellas, se recupera lo necesario sobre una rama nueva desde el `main` actualizado.
- Después de integrar, la rama se elimina automáticamente.

## Fotografía actual — 26/11/2026, después de la integración de PR #363

- `main` está en [`df3a6f3`](https://github.com/JavierGrecco/prestamos_privados/commit/df3a6f30a068f5fd59565fe31b41b13a8ff4f4b4).
- La consulta de GitHub registra **16 ramas: `main` y 15 ramas históricas preservadas**; no había PR abierta en el chequeo inmediatamente posterior al merge de #363.
- Las 15 ramas históricas muestran divergencia con `main` y commits propios. Por eso no se consideran contenidas ni se borran por antigüedad.
- PR #361 integró la corrección de ancestralidad y actualizó `actions/github-script` a v9 (Node 24).
- PR #363 integró los contratos de error de persistencia sin cambiar el motor Legacy ni las reglas financieras.
- La matriz post-merge aprobó 1.311 pruebas por cada Python 3.11–3.14; CodeQL, auditoría de dependencias y branch housekeeping terminaron correctamente ([pruebas](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45876202477) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45876202484) · [limpieza](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45876202591)).
- La limpieza posterior al merge retiró la rama temporal ya integrada, sin borrar las 15 ramas históricas preservadas.
- El inventario de las 15 ramas y su motivo de preservación está arriba. Cada recuperación debe hacerse sobre una rama nueva desde el `main` actualizado.

La ejecución anterior que terminó en error se conserva como evidencia histórica. PR #360 hizo idempotente el borrado frente a referencias ausentes y PR #361 corrigió el criterio de ancestralidad: con `branch...main`, `behind_by` debe ser cero y el estado debe ser `ahead` o `identical`. PR #363 no modificó la automatización de ramas; el workflow sigue usando `actions/github-script@v9` y Node 24.
