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
- en cada actualización de `main`, elimina las ramas históricas cuyo nombre y SHA coinciden exactamente con el HEAD de una PR integrada en `main`;
- al cerrar una PR integrada, elimina también su rama de trabajo actual;
- permite inventariar las ramas históricas en modo **DRY RUN**;
- solo borra ramas históricas cuando se ejecuta manualmente con `dry_run=false` y la confirmación exacta `DELETE_MERGED_BRANCHES`;
- por defecto considera únicamente ramas cuyo SHA coincide con el HEAD de una PR ya integrada en `main`;
- opcionalmente incluye PR cerradas solo cuando su cuerpo dice expresamente que fueron sustituidas y cita otra PR ya integrada;
- nunca elimina `main`, ramas protegidas, ni ramas con una PR abierta.

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
| Ramas cuyo HEAD coincide con PR cerradas sin merge | 36 | 12 tienen sustitución explícita; 24 requieren revisión |
| Ramas sin PR cerrada asociada | 18 | Preservar hasta revisar si contienen trabajo único |
| Rama estable `main` | 1 | Conservar siempre |
| Rama de la PR abierta #357 | 1 | Conservar hasta integrar; luego entra en la limpieza automática |

El número de PR cerradas no es igual al número de ramas: algunas ramas ya no existen y puede haber PR antiguas con más de una iteración. El workflow exige coincidencia exacta entre nombre de rama y SHA del HEAD de la PR para evitar borrar una rama que haya avanzado después de la integración. Al integrar la PR #357, la ejecución sobre el nuevo commit de `main` debería encontrar 238 ramas aptas para borrado (las 237 actuales más la rama de la propia PR); deberían quedar 56 ramas: `main`, las 36 asociadas a PR cerradas sin merge, la rama con SHA divergente y las 18 huérfanas.

La primera ejecución manual debe ser un **DRY RUN**. El resumen real de GitHub Actions es la lista definitiva de candidatos; estas cifras son el inventario observado antes de ejecutar la limpieza.
