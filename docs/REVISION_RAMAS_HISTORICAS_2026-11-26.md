# Revisión y consolidación de ramas históricas

**Fecha:** 26 de noviembre de 2026  
**Base auditada:** `main` en `1192e5d3dca1515ecd0b1baf5ba8284d2e9d4908` (posterior a PR #387).  
**Inventario observado:** 15 referencias: `main` y 14 ramas históricas; cero PR abiertas.  
**Resultado buscado:** una sola referencia de revisión para el trabajo todavía rescatable, sin integrar a ciegas código antiguo.

## Decisión de consolidación

No se hizo un merge funcional masivo. Cada rama fue comparada con `main`, y las capacidades se contrastaron con los servicios, tests y PR posteriores. Las ramas reemplazadas se retiran mediante un manifiesto que fija el nombre y SHA exactos. El workflow vuelve a comprobar que el SHA no cambió, que no está protegida, que no es `main` y que ninguna PR abierta la utiliza. Un mismatch conserva la rama y genera una advertencia.

La fuente histórica de M5 se conserva con el mismo commit en `review/m5-rendimiento-operaciones`; el nombre original `feature/m5-rendimiento-operaciones` se retira. El issue [#388](https://github.com/JavierGrecco/prestamos_privados/issues/388) exige portar la funcionalidad usando la arquitectura actual. La rama de revisión es un archivo de referencia, no una base válida para desarrollar sobre los más de 300 commits que quedó detrás de `main`.

## Inventario verificado

| Rama histórica | HEAD verificado | Decisión y evidencia |
|---|---|---|
| `chore/security-automation` | `40eab3a7` | Retirar la referencia antigua. `SECURITY.md`, Dependabot y CodeQL ya están en `main`; Dependency Review queda pendiente de validar/habilitar Dependency Graph en [#389](https://github.com/JavierGrecco/prestamos_privados/issues/389). No duplicar CodeQL ni declarar ese check activo antes de probarlo. |
| `docs/update-mvp-status-after-pr237-20261010` | `0e5fe339` | Retirar. Documentación de octubre superada por estado y roadmap posteriores, incluido PR #387. |
| `feat/benchmark-cagr-freshness-20261010` | `85ded324` | Retirar. El guardarraíl de antigüedad máxima de 90 días ya está en `main`; se recupera aquí su prueba E2E de serie antigua y fixtures temporales. |
| `feat/redisenio-visual-oscuro-d4` | `8d46ce49` | Retirar la rama antigua, no el trabajo de UX pendiente. El tema oscuro es predeterminado en `main`; la navegación y el shell evolucionaron. La aceptación visual manual sigue abierta en [#177](https://github.com/JavierGrecco/prestamos_privados/issues/177). |
| `feature/i1-sombra-snapshot` | `a9d416c4` | Retirar. El ejecutor SOMBRA de `main` ya incluye snapshot previo, aislamiento de errores, detección idempotente previa y cierre de carrera dentro de Legacy; supera esta versión histórica. |
| `feature/k16-ui-exports-v2` | `4ea74e3b` | Retirar. Las exportaciones se implementaron posteriormente con servicios, puertos y composición actuales; no volver a incorporar sus constructores directos. |
| `feature/l1-2-validar-evidencia-canary` | `fe222a6f` | Retirar. Su propuesta fue sustituida por el paquete reproducible de decisión integrado en [PR #133](https://github.com/JavierGrecco/prestamos_privados/pull/133); el cierre está explicado en [PR #131](https://github.com/JavierGrecco/prestamos_privados/pull/131). |
| `feature/m5-rendimiento-operaciones` | `99eabec1` | Retirar el nombre original y conservar el mismo HEAD en `review/m5-rendimiento-operaciones`. La funcionalidad por operación no está en `main`, pero su consulta histórica depende directamente de `BaseDatos` y `PersonaRepo` desde aplicación. Reimplementación pendiente en [#388](https://github.com/JavierGrecco/prestamos_privados/issues/388), sin merge directo. |
| `feature/m6-reporte-financiero-persona` | `82f959eb` | Retirar. Reporte personal reemplazado por la implementación integrada en [PR #119](https://github.com/JavierGrecco/prestamos_privados/pull/119); cierre documentado en [PR #120](https://github.com/JavierGrecco/prestamos_privados/pull/120). |
| `feature/ui-rendimiento-objetivo-usd` | `90865510` | Retirar. El flujo analítico USD ya está incorporado a la pantalla principal del simulador; el componente aislado de la rama no está conectado y no conviene introducir código muerto. |
| `fix/ui-sqlite-connection-lifecycle` | `09f303da` | Retirar. El ciclo de apertura y composición se rediseñó en [PR #367](https://github.com/JavierGrecco/prestamos_privados/pull/367) y el aislamiento por sesión se validó en [PR #369](https://github.com/JavierGrecco/prestamos_privados/pull/369). |
| `refactor/auditoria-read-port` | `33f8878b` | Retirar. El contrato y la composición actuales están integrados; la evolución posterior se encuentra en [PR #284](https://github.com/JavierGrecco/prestamos_privados/pull/284). |
| `refactor/historial-pagos-read-port` | `d90f8620` | Retirar. El puerto público, el adaptador SQLite y la composición ya existen en `main`; la rama no aporta una implementación actual que deba fusionarse. |
| `refactor/ui-alta-prestamo-servicio-personas-20261015` | `5aa0b73f` | Retirar. La pantalla ya consulta personas a través de `crear_servicio_personas`; se recupera su guarda arquitectónica como test de `main`. |

## Mejoras recuperadas en esta consolidación

- El workflow de housekeeping acepta una lista explícita de retiros revisados, pero exige coincidencia exacta de SHA, referencia no protegida, rama distinta de la predeterminada y ausencia de PR abierta. Las reglas anteriores de coincidencia con PR integradas y ancestralidad permanecen intactas.
- Se agrega una prueba que protege el contrato del manifiesto y otra que impide que el alta de préstamo vuelva a consultar repositorios directamente.
- El test E2E de benchmark usa fechas relativas, datos total-return reproducibles y verifica que una serie continua pero antigua (más de 90 días desde su última observación) no pueda alimentar la tasa base actual. El backtest histórico cubierto permanece disponible.
- No se incorpora Dependency Review todavía: primero debe comprobarse la capacidad Dependency Graph y el check real. [#389](https://github.com/JavierGrecco/prestamos_privados/issues/389) registra ese prerrequisito. CodeQL y `pip-audit` siguen activos.

## Verificación posterior obligatoria

El manifiesto [`branch-retirement-manifest.json`](branch-retirement-manifest.json) registra las 14 referencias originales y sus SHAs exactos. Al integrar esta PR, el push a `main` disparará housekeeping. No se dará por completada la limpieza por el mero merge: hay que inspeccionar el resumen del workflow y volver a consultar las referencias.

**Resultado esperado, sujeto a esa verificación:** `main` y una sola rama de revisión, `review/m5-rendimiento-operaciones`. La rama de consolidación también debe desaparecer al cerrar su PR integrada. No borrar manualmente una rama cuyo SHA cambió o que tenga una PR abierta.

## Lo que esta limpieza no significa

- No declara el MVP aceptado ni listo para producción; #223 y las pruebas manuales siguen pendientes.
- No fusiona el contenido antiguo de M5 ni suprime su deuda arquitectónica; #388 lo mantiene como trabajo post-MVP.
- No cierra la validación visual de D4; #177 sigue abierto.
- No declara Dependency Review habilitado; #389 permanece abierto.
- No modifica cálculos, contratos, pagos, ledger ni datos financieros.
