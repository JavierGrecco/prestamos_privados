# Revisión y consolidación de ramas históricas

**Fecha:** 26 de noviembre de 2026  
**Base auditada:** `main` en `1192e5d3dca1515ecd0b1baf5ba8284d2e9d4908`, posterior a PR #387.  
**Inventario inicial:** 15 referencias — `main` y 14 ramas históricas — sin PR abiertas.

## Decisión: archivar la historia, no mezclar el código

Se creó el anclaje Git final `archive/legacy-branches-2026-11` en el commit `29ab117ee384d9809a6944d0f9997d6207bb4c92`. Verificación directa de GitHub:

- El commit final tiene dos padres: el anclaje de las 14 ramas (`0f22a23d`) y la implementación histórica de housekeeping (`0f02bdf`).
- El anclaje previo de las 14 ramas tiene exactamente **15 padres**: el `main` original y los 14 HEAD históricos.
- El árbol del commit final es `0ff8027f4f23b0670cb2ef76c868a093e0081ef8`, idéntico al árbol del `main` de base.
- La comparación de `main...archive` no muestra archivos modificados.

Esto conserva todas las historias como alcanzables desde una sola referencia sin aplicar sus árboles viejos a `main` ni afirmar que las funcionalidades pendientes están integradas. La descripción técnica está en [Archivo de ramas históricas](ARCHIVO_RAMAS_HISTORICAS.md); el inventario máquina-readable está en [ARCHIVO_RAMAS_HISTORICAS_2026-11.json](ARCHIVO_RAMAS_HISTORICAS_2026-11.json).

## Inventario y decisión por rama

| Rama original | HEAD | Decisión |
|---|---|---|
| `chore/security-automation` | `40eab3a7` | La seguridad base ya está consolidada en `main` con CodeQL, Dependabot, `pip-audit` y SECURITY.md. Dependency Review no se activa hasta resolver el prerequisito del Dependency Graph (#389). No fusionar la copia antigua. |
| `docs/update-mvp-status-after-pr237-20261010` | `0e5fe339` | Snapshot documental de octubre superado por estado, roadmap y validaciones de noviembre. Conservar en el anclaje, no como rama activa. |
| `feat/benchmark-cagr-freshness-20261010` | `85ded324` | El control de frescura ya está en `main`; se recupera su test E2E útil con fechas relativas y una serie continua pero antigua. La implementación vieja del simulador no se trae en bloque. |
| `feat/redisenio-visual-oscuro-d4` | `8d46ce49` | `main` ya tiene tema oscuro predeterminado y navegación evolucionada. La aceptación visual manual sigue pendiente en #177; preservar el snapshot como referencia, no como merge candidato. |
| `feature/i1-sombra-snapshot` | `a9d416c4` | El ejecutor SOMBRA actual evolucionó con snapshot previo, aislamiento de errores e idempotencia. No activar cut-over ni volver a integrar la versión antigua. |
| `feature/k16-ui-exports-v2` | `4ea74e3b` | Exportaciones ya integradas mediante servicios, puertos y composición actuales. No recuperar la implementación histórica. |
| `feature/l1-2-validar-evidencia-canary` | `fe222a6f` | El paquete de decisión L1.2 llegó por PR #133 y reemplazó el flujo coordinado en #131. El validador/CLI histórico queda preservado para inspección, no declarado funcional actual ni habilitado. Revisar contra v026 y #145 antes de cualquier adaptación. |
| `feature/m5-rendimiento-operaciones` | `99eabec1` | Propuesta de rendimiento/XIRR por operación útil, pero el read model importa `BaseDatos` y `PersonaRepo` desde aplicación. Preservar el commit como padre del anclaje; reimplementar con puertos y composición en #388, sin merge directo. |
| `feature/m6-reporte-financiero-persona` | `82f959eb` | El reporte personal fue implementado luego por PR #119. La rama antigua conserva una versión distinta; no reintroducirla sin comparación funcional. |
| `feature/ui-rendimiento-objetivo-usd` | `90865510` | La simulación USD está en la pantalla actual, pero el componente aislado antiguo no está conectado. Conservar como referencia de UX futura; no introducir código muerto. |
| `fix/ui-sqlite-connection-lifecycle` | `09f303da` | Reemplazada por apertura/composición SQLite en #367 y aislamiento por sesión en #369. No integrar el ciclo de vida anterior. |
| `refactor/auditoria-read-port` | `33f8878b` | El contrato y la composición actuales evolucionaron y quedaron integrados, incluida la línea #284. Conservar como historial. |
| `refactor/historial-pagos-read-port` | `d90f8620` | Puerto, adaptador y composición de lectura ya evolucionaron en `main`. No integrar la implementación vieja. |
| `refactor/ui-alta-prestamo-servicio-personas-20261015` | `5aa0b73f` | La pantalla actual ya usa el servicio público de personas. Se recupera su guarda arquitectónica como test en `main`; no es necesario fusionar la rama. |

## Mejoras recuperadas en la PR de consolidación

- El housekeeping toma el manifiesto histórico anclado y verifica el commit/árbol/padres exactos, SHA vivo de cada rama, protección, PR abierta y alcanzabilidad real antes de retirar una referencia.
- El anclaje se excluye explícitamente de la limpieza genérica por ancestralidad, del borrado al cerrar PR y del modo manual. Sin esta guarda podría eliminarse por error al quedar como antecesor de `main`.
- Se recupera la prueba arquitectónica del alta de préstamo: la UI debe usar el servicio público de personas y no construir repositorios.
- Se recupera la prueba E2E de frescura del benchmark, con fixtures dinámicos y cobertura de serie antigua.
- README, estado, índice y flujo Git quedan alineados con la validación real posterior a PR #387.

## Resultado esperado y comprobación

Después de integrar la PR, el housekeeping debe retirar las 14 referencias originales solo después de verificar que cada HEAD está preservado como padre/ancestro del anclaje. La limpieza genérica puede retirar las ramas temporales ya contenidas (incluidas las dos ramas auxiliares de consolidación y el alias de revisión M5), pero nunca el anclaje.

**Resultado final esperado: dos referencias: `main` y `archive/legacy-branches-2026-11`.** No se declarará completado hasta revisar el resumen del workflow y consultar de nuevo las ramas en GitHub.

El anclaje es de solo lectura. No se abre trabajo ni PR sobre él. Todo desarrollo futuro parte de `main` y usa una sola rama temporal activa.

## Lo que esta limpieza no significa

- No integra en bloque los catorce HEAD ni declara terminadas las funcionalidades históricas.
- No cierra el issue M5 #388, la aceptación visual #177 ni el prerequisito de Dependency Review #389.
- No modifica cálculos, contratos, pagos, amortización, ledger ni datos financieros.
- No declara el MVP aceptado ni listo para producción; #223 y la aceptación funcional/operativa siguen pendientes.
