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
| Ramas sin PR cerrada asociada | 18 | Preservar hasta revisar si contienen trabajo único |
| Rama estable `main` | 1 | Conservar siempre |
| Rama de la PR abierta #357 | 1 | Conservar hasta integrar; luego entra en la limpieza automática |

El número de PR cerradas no es igual al número de ramas: algunas ramas ya no existen y puede haber PR antiguas con más de una iteración. Para las PR integradas se exige coincidencia exacta entre nombre de rama y SHA del HEAD, para evitar borrar una rama que haya avanzado después de la integración. Para ramas sin esa coincidencia, solo se borran si el commit completo ya es antecesor de `main`; cualquier rama divergente o con commits únicos queda preservada. Al integrar la PR #357, la limpieza debería eliminar como mínimo las 238 ramas integradas exactas (las 237 actuales más la rama de la propia PR), las 18 ramas con sustitución documentada y las ramas adicionales cuyo HEAD ya esté contenido en `main`. El número final lo informará el resumen de GitHub Actions; no se fija un total estimado para las ramas que requieren comparación de ancestros.

La primera ejecución manual debe ser un **DRY RUN**. El resumen real de GitHub Actions es la lista definitiva de candidatos; estas cifras son el inventario observado antes de ejecutar la limpieza.
