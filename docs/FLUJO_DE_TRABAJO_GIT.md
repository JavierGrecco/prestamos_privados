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

## Fotografía actual — 26/11/2026, después de la integración de PR #372

- `main` está en [`0bae21f`](https://github.com/JavierGrecco/prestamos_privados/commit/0bae21fd44918d8d3c2140311406755bbaba8954).
- La consulta de GitHub inmediatamente después del merge registró **16 ramas: `main` y 15 ramas históricas preservadas**. Las ramas históricas siguen siendo divergentes y no se borran por antigüedad.
- Las 15 ramas históricas muestran divergencia con `main` y commits propios. Por eso no se consideran contenidas ni se borran por antigüedad.
- `main` todavía no está protegida por una ruleset o branch protection administrativa; la configuración y los checks requeridos siguen pendientes en [#157](https://github.com/JavierGrecco/prestamos_privados/issues/157).
- PR #361 integró la corrección de ancestralidad y actualizó `actions/github-script` a v9 (Node 24).
- PR #363 integró los contratos de error de persistencia, PR #365 inició la deprecación gradual del constructor Legacy sin retirarlo, PR #367 movió el ciclo de apertura de SQLite desde la UI hacia composición y PR #369 aisló conexiones SQLite por sesión. PR #372 sincronizó documentación de producto, estado y operación sin cambiar código ejecutable.
- El inventario post-merge del commit actual analizó 318 archivos Python sin errores: 1.697 importaciones, 303 cruces, 55 hallazgos (7 pendientes, 3 excepciones y 45 usos de composición) y cero ciclos.
- La matriz post-merge aprobó 1.325 pruebas por cada Python 3.11–3.14; CodeQL, auditoría de dependencias y branch housekeeping terminaron correctamente ([pruebas](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45887341184) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45887341158) · [limpieza](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45887341151)).
- La limpieza posterior al merge retiró las ramas temporales integradas, incluidas las de PR #371 y #372, sin borrar las 15 ramas históricas preservadas. El corte posterior al merge de #372 y anterior a abrir la PR documental #373 contaba 16 referencias: `main` y 15 ramas históricas, sin PRs abiertas. La rama temporal de la presente revisión se elimina al integrar #373.
- El inventario de las 15 ramas y su motivo de preservación está arriba. Cada recuperación debe hacerse sobre una rama nueva desde el `main` actualizado.

La ejecución anterior que terminó en error se conserva como evidencia histórica. PR #360 hizo idempotente el borrado frente a referencias ausentes y PR #361 corrigió el criterio de ancestralidad: con `branch...main`, `behind_by` debe ser cero y el estado debe ser `ahead` o `identical`. PR #363 no modificó la automatización de ramas; el workflow sigue usando `actions/github-script@v9` y Node 24.


## Reauditoría de ramas — 26/11/2026

### Fotografía verificada

Base de comparación: `main` en `9bf4a832` (posterior a PR #385). GitHub informó **17 referencias durante esta revisión**: `main`, 15 ramas históricas existentes y la rama temporal de esta corrección. No hay PR abiertas.

La revisión encontró una rama histórica sin contenido exclusivo:

- `feature/m4-escenarios-planificacion-v2`, HEAD `6d0b43f3`, contiene un único commit (`feat(m4): expone factor de escenario mensual reutilizable`).
- El commit tiene un solo padre (`b975c3ca`), y ambos tienen exactamente el mismo árbol Git (`c2be5cb5`). La API de commit devuelve cero archivos modificados.
- El padre está contenido en `main`: la comparación padre...`main` devuelve `behind_by = 0`.
- No hay PR abierta que utilice la rama y la referencia figura sin protección.

Por lo tanto, ese commit no agrega código, pruebas ni documentación. Se amplió la automatización para reconocer exclusivamente este caso cuando se cumplan todas estas condiciones: un solo commit exclusivo, un único padre, árbol idéntico al padre y padre contenido en `main`. Si una consulta falla o no puede probarse alguna condición, la rama se conserva y se registra una advertencia. La protección de rama y las PR abiertas siguen excluyendo cualquier candidato.

La eliminación se ejecutará automáticamente en el próximo `push` a `main`, después de integrar esta corrección. **No se da por eliminada hasta consultar nuevamente las referencias y comprobar el resultado del workflow.**

### Las otras 14 ramas históricas

Las siguientes ramas conservan commits exclusivos. Las cifras son la salida de GitHub Compare contra `main`: commits exclusivos, commits posteriores en `main` y cantidad de archivos con diferencias. No miden calidad ni justifican un merge.

| Rama | Exclusivos | Main posterior | Archivos diferentes |
|---|---:|---:|---:|
| `chore/security-automation` | 5 | 455 | 5 |
| `docs/update-mvp-status-after-pr237-20261010` | 6 | 246 | 4 |
| `feat/benchmark-cagr-freshness-20261010` | 5 | 261 | 2 |
| `feat/redisenio-visual-oscuro-d4` | 15 | 287 | 12 |
| `feature/i1-sombra-snapshot` | 15 | 743 | 5 |
| `feature/k16-ui-exports-v2` | 8 | 406 | 7 |
| `feature/l1-2-validar-evidencia-canary` | 9 | 321 | 7 |
| `feature/m5-rendimiento-operaciones` | 14 | 328 | 10 |
| `feature/m6-reporte-financiero-persona` | 14 | 326 | 10 |
| `feature/ui-rendimiento-objetivo-usd` | 1 | 278 | 1 |
| `fix/ui-sqlite-connection-lifecycle` | 4 | 377 | 3 |
| `refactor/auditoria-read-port` | 13 | 210 | 12 |
| `refactor/historial-pagos-read-port` | 7 | 208 | 7 |
| `refactor/ui-alta-prestamo-servicio-personas-20261015` | 2 | 41 | 2 |

Estas ramas son **archivo histórico, no trabajo activo**. No se integrarán en bloque ni se usarán como base para nuevo desarrollo. Para rescatar una capacidad, primero se compara su implementación con `main`; después se porta solo lo que siga siendo necesario a una única rama nueva creada desde el `main` actualizado, con pruebas actuales. Lo reemplazado u obsoleto se descarta con evidencia y por separado.

### Orden sugerido para la segunda revisión

1. Seguridad y automatización: `chore/security-automation` (contrastar workflows y `SECURITY.md` actuales; no duplicar CodeQL/auditoría existentes).
2. Funcionalidad potencialmente útil: exportaciones K16, reportes M5/M6 y rendimiento USD; validar integración actual, permisos, consistencia y pruebas antes de rescatar.
3. V3/canary y sombra: revisar `feature/i1-sombra-snapshot` y `feature/l1-2-validar-evidencia-canary` contra issues #74 y #145. No habilitar cut-over ni cambiar autoridad financiera.
4. UI y consultas: comparar rediseño, historial de pagos, auditoría y alta de préstamo. No reemplazar implementaciones actuales sin demostrar ventaja y compatibilidad.

La revisión no convierte estas prioridades en ramas activas. Se trabaja con una sola rama y una única PR en cada ciclo.

### Protección de main

La consulta de ramas devolvió `protected=false` para las referencias y no se encontraron rulesets visibles. El endpoint clásico de protección de `main` no estuvo disponible para esta integración (HTTP 403), por lo que no afirmo haber verificado todos sus detalles. La configuración administrativa sigue pendiente en [#157](https://github.com/JavierGrecco/prestamos_privados/issues/157). La automatización de limpieza no sustituye la protección de `main`.


## Resultado de limpieza conservadora — PR #386, 26/11/2026

La reauditoría anterior identificó un único caso histórico sin contenido exclusivo: `feature/m4-escenarios-planificacion-v2`. El commit de esa rama tenía exactamente el mismo árbol que su padre y el padre ya estaba en `main`. PR [#386](https://github.com/JavierGrecco/prestamos_privados/pull/386) incorporó esa validación estrecha a housekeeping. La comparación respeta `branch...main`: el commit exclusivo se contabiliza en `behind_by`.

La ejecución por push a `main` [#49](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45907769283) terminó correctamente y reportó la eliminación de la rama M4. La limpieza al cerrar la PR [#386](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45907769820) retiró la rama temporal de trabajo.

**Resultado comprobado: 15 referencias totales — `main` y 14 ramas históricas preservadas.** No hay PR abiertas al finalizar esa entrega. Las 14 ramas no se borran ni integran en bloque porque contienen commits exclusivos. Siguen siendo archivo de recuperación, no líneas activas de desarrollo.

El CI post-merge de `main` aprobó 1.370 pruebas por cada Python 3.11–3.14, CodeQL y auditoría de dependencias ([tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45907769153) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45907769135)). La política permanece: una rama activa, una PR a `main`, squash merge y limpieza de la rama integrada.
