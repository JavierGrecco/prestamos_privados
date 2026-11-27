# Revisión técnica integral — actualización del 26 de noviembre de 2026

## Addendum de evidencia — posterior a PR #406, 27 de noviembre de 2026

Este corte actualiza la evidencia operativa desde el HEAD de `main`. La revisión arquitectónica y la valoración histórica que siguen conservan sus cortes originales.

- **HEAD de `main`:** [7b5a714](https://github.com/JavierGrecco/prestamos_privados/commit/7b5a714fb5d8a081e2db52a3fa9db628b0fe0aa2), PR #406.
- **Restore E2E:** `tests/test_restore_drill_sintetico.py` ejecuta el entrypoint real `ui/app.py` con `PRESTAMOS_DB_PATH` apuntando a la restauración. Comprueba el estado de primer arranque, crea un ADMIN sintético en la copia, inicia un segundo contexto que reconoce la cuenta y presenta login, autentica esa sesión y vuelve a consultar préstamo, pago y ledger. La cuenta de prueba no se crea en el origen.
- **Límite operativo:** `AppTest` no cierra y reinicia un proceso Streamlit real ni verifica la interfaz en un navegador. #374 continúa abierto hasta completar el restore manual; #223 continúa abierto como aceptación P0 del MVP.
- **Validación post-merge:** 1.420 pruebas en cada Python 3.11, 3.12, 3.13 y 3.14; CodeQL y `pip-audit` aprobados. [Tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45937308452) · [Seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45937308462) · [Housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45937308479).
- **GitHub:** PR #406 fue integrada por squash. Housekeeping eliminó la rama temporal y dejó `main` más `archive/legacy-branches-2026-11`, sin PR abiertas. `main` no está protegida (`protected: false`); #157 sigue pendiente.
- **Arquitectura:** PR #406 modifica solo pruebas y documentación. El inventario modular detallado sigue siendo el corte post-PR #402, no una nueva ejecución; las 7 construcciones pendientes de migración de #270 siguen abiertas.
- **Sin cambios económicos:** no se modificaron contratos, tasas, pagos, cuotas, migraciones, ledger ni snapshots del dominio.

## Addendum histórico — posterior a PR #404, 27 de noviembre de 2026

Este corte describe el estado posterior a PR #404 y se conserva como antecedente. El estado vigente posterior a PR #406 está documentado en el addendum inicial.

- **HEAD de `main`:** [d68a696](https://github.com/JavierGrecco/prestamos_privados/commit/d68a696c0f8efef2ab6dd3a96a6e440ce1f0954c), PR #404.
- **Cambio funcional:** los cobros externos futuros ahora distinguen `DECLARADO` y `REFERENCIA_DOCUMENTAL_DECLARADA`. La aplicación exige una referencia escrita para la segunda categoría, pero no recibe, almacena ni valida el documento; tampoco verifica a quien debe pagar. Ambas categorías conservan igual peso en la evaluación. La entrada continúa en ARS y solo en sesión.
- **Validación post-merge:** 1.420 pruebas aprobadas en cada Python 3.11, 3.12, 3.13 y 3.14; CodeQL, `pip-audit` y branch housekeeping aprobaron. [Tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45934267143) · [Seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45934267125) · [Housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45934267141).
- **GitHub en el corte estable inmediatamente posterior a #404:** no había PR abiertas y solo permanecían `main` y `archive/legacy-branches-2026-11`. La actualización documental actual se tramita en la única rama temporal de PR #405, que se retirará tras el merge y housekeeping. El endpoint informa `protected: false` para `main`; la protección administrativa continúa pendiente en #157.
- **Aceptación:** #223 sigue abierto. El restore drill sintético está automatizado, pero el paso manual de abrir y reiniciar la UI con la copia restaurada sigue pendiente en #374; también sigue pendiente la aceptación E2E de pagos concurrentes (#159).
- **Alcance:** PR #404 no cambia contratos, cuotas, pagos, ledger, auditoría, persistencia personal ni autoridad Legacy/V3. El inventario modular detallado continúa siendo el corte post-PR #402, no un análisis nuevo de PR #404.

## Addendum histórico de evidencia — posterior a PR #402

Este corte describe PR #402 y se conserva como antecedente. El estado vigente posterior a PR #404 está documentado en el addendum inicial.

- **Último cambio funcional de main:** commit [bf12bb6](https://github.com/JavierGrecco/prestamos_privados/commit/bf12bb68bbcd1853c4a0dc312c136f11b2839c35), PR #402.
- **PR #400 — F1.2:** integra cobros contractuales del rol inversor provenientes de AnalisisFinancieroQuery.flujos_proyectados con cobros externos declarados. Conserva referencias, subtotales por fuente y detalle por período; rechaza referencias contractuales repetidas. Por defecto, los cobros contractuales se consideran incluidos en el margen para evitar doble conteo; la persona puede desmarcarlo.
- **PR #402 — comparación contractual:** permite generar una propuesta con el mismo simulador de alta y comparar todas sus cuotas (1–360) y vencimientos exactos contra el margen habitual y ajustado. La caja/reserva utiliza esos faltantes variables y los cobros por fecha, pero solo para los primeros 1–24 vencimientos seleccionados. No se extrapolan supuestos de estrés o disponibilidad de cobros durante todo el contrato.
- **Límites preservados:** la propuesta es una simulación y no se persiste. Los cobros externos siguen siendo datos declarados en ARS y en sesión; no se convierten en pagos reales ni se escriben en SQLite, ledger o auditoría. No se crea una segunda amortización.
- **CI post-merge de PR #402 sobre `main`:** 1.417 pruebas aprobadas en cada Python 3.11, 3.12, 3.13 y 3.14; CodeQL, `pip-audit` y branch housekeeping aprobados. [Tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45925783542) · [Seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45925783576) · [Housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45925783547).
- **Inventario modular post-merge:** 323 archivos Python analizados sin errores, 1.747 importaciones, 318 cruces entre capas y 54 hallazgos: 7 pendientes de migración, 1 excepción temporal documentada y 46 usos de composición de borde. Se detectaron cero ciclos. Este inventario confirma que los 7 pendientes siguen abiertos y no cierra la issue #270.
- **GitHub:** la documentación de este corte se preparó en una única rama temporal. Tras su integración por squash, housekeeping debe retirarla; el inventario estable queda en `main` y `archive/legacy-branches-2026-11`. El anclaje conserva los 14 HEAD históricos y no se fusiona con `main`.
- **Límites de #270:** sigue abierto hasta migrar los siete constructores de repositorio y verificar consumidores; no se declara cerrada la deuda arquitectónica.
- **Límite de F1.2:** la proyección conjunta y la comparación del cronograma completo ya están integradas. Siguen pendientes calidad/evidencia de cobros externos y conciliación al recibir. El estrés de caja/reserva se limita a 1–24 vencimientos elegidos; no cubre automáticamente el plazo completo de propuestas de hasta 360 cuotas.
- **Límite de producto:** el MVP local continúa sin aceptación funcional/operativa integral. CI verde no sustituye recorridos manuales, conciliación financiera, restore drill independiente ni prueba de concurrencia.


## Alcance y método

La línea de base analítica histórica toma como referencia main en [feb12a0](https://github.com/JavierGrecco/prestamos_privados/commit/feb12a020dfd53e3fad9ceccda646e7e9065598e), que incorpora PR #384. Los cortes de PR #393, PR #395 y PR #402 se conservan como antecedentes; el estado vigente posterior a PR #404 se describe en el addendum inicial.

Se revisaron el árbol y la documentación del repositorio, las capas de aplicación/infraestructura/UI, el read model de flujos financieros, las pruebas nuevas, el workflow de PR #384, los logs de cada versión de Python, el inventario modular y el estado de issues, PRs y ramas.

Esta revisión no equivale a una auditoría externa, un pentest, una aceptación manual de la interfaz, una prueba de restauración real ni una validación con dinero o datos productivos. La nota para liderazgo técnico es una valoración razonada, no una métrica generada automáticamente.

## Conclusión ejecutiva

**Préstamos Privados es un proyecto técnicamente serio y atractivo para revisar en una entrevista de ingeniería, pero todavía no es un producto local aceptado ni está listo para producción.**

El repositorio demuestra más que una colección de pantallas: contiene un dominio financiero con reglas y estados diferenciados, una arquitectura por capas, consultas de lectura reutilizables, ledger y auditoría, controles de idempotencia/rollback, pruebas E2E y una matriz CI amplia. Las últimas mejoras de capacidad de pago y cobros futuros reutilizan información financiera existente, en lugar de crear un segundo motor de amortización.

La brecha principal ya no es solamente escribir más funcionalidades. Es cerrar la aceptación del producto: reglas contractuales pendientes, conciliación de los recorridos desde la UI, concurrencia financiera, restauración de backup, migraciones históricas y protección administrativa de `main`.

## Evidencia histórica de PR #384 — anterior a su integración

La PR #384 fue integrada mediante squash en el commit `feb12a0`. Su head pasó los checks antes del merge:

| Control | Resultado comprobado | Alcance |
|---|---:|---|
| Python 3.11 | **1.369 pruebas aprobadas** | Suite completa |
| Python 3.12 | **1.369 pruebas aprobadas** | Suite completa |
| Python 3.13 | **1.369 pruebas aprobadas** | Suite completa |
| Python 3.14 | **1.369 pruebas aprobadas** | Suite completa |
| Compilación | Aprobada | Workflow de tests |
| Consistencia de dependencias | Aprobada | `pip check` |
| Inventario modular | Aprobado | AST, límites y ciclos |
| CodeQL | Aprobado | Configuración existente del repositorio |
| Auditoría de dependencias | Aprobada | `pip-audit` |

Evidencia: [matriz de pruebas — run 45904847625](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45904847625) · [seguridad — run 45904847569](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45904847569) · [PR #384](https://github.com/JavierGrecco/prestamos_privados/pull/384).

Las 1.369 pruebas son el total de una suite en cada intérprete; no deben sumarse para afirmar que existen 5.476 pruebas diferentes. Los resultados corresponden al head validado de la PR, no a una aceptación manual ni a una ejecución con datos productivos.

### Incidente de CI observado y resuelto

La primera ejecución de PR #384 encontró dos fallas de integración en Python 3.11:

- una guarda arquitectónica requería que el argumento de base de datos de una pantalla se anotara como `object`;
- una prueba E2E suponía incorrectamente que una persona de la fixture no tenía rol inversor.

Se corrigió la anotación y se retiró la premisa incorrecta de la prueba. La ejecución posterior aprobó las 1.369 pruebas en las cuatro versiones de Python y los controles de seguridad. No hay un issue #456 registrado en este repositorio; si la referencia del reporte del usuario apunta a otro run o a un fallo local, se necesita ese log concreto para identificarlo.

## Inventario de arquitectura — corte histórico de PR #384

El inventario de la última ejecución analizó:

- **320 archivos Python**, sin errores de análisis;
- 1.712 importaciones, de las cuales 308 cruzan límites entre capas;
- 56 hallazgos en 26 archivos;
- 7 pendientes de migración;
- 3 excepciones temporales documentadas;
- 46 usos de composición clasificados en los bordes permitidos;
- **cero ciclos de importación**.

El reporte clasificó 10 hallazgos con severidad alta —los 7 pendientes y las 3 excepciones documentadas— y 46 informativos/de composición. No significa que existan 56 defectos equivalentes: los puntos de composición son ensamblados de dependencias; los siete pendientes y tres excepciones sí requieren seguimiento explícito.

Esta medición es una herramienta para gobernar la modularización, no un porcentaje de arquitectura terminada.

## Fortalezas demostrables

### 1. Dominio financiero y trazabilidad

El sistema utiliza `Decimal`, contratos de aplicación, transacciones, idempotencia, rollback, ledger, auditoría y snapshots en áreas concretas. Los pagos parciales, adelantos, mora y distribución entre inversores son problemas de dominio reales y más interesantes que un CRUD genérico.

La cautela con las diferencias Legacy/V3 es correcta: Legacy permanece como autoridad operativa mientras no se resuelvan las divergencias documentadas en [#145](https://github.com/JavierGrecco/prestamos_privados/issues/145). No activar V3 por cantidad de tests o conveniencia de implementación.

### 2. Separación por capas en evolución

El dominio conserva reglas económicas; aplicación concentra casos de uso y consultas; infraestructura conecta puertos, SQLite y composición; Streamlit presenta la experiencia. Se trasladó la apertura/migración de base fuera de la UI y se aislaron recursos SQLite por sesión.

La separación no está completa: el inventario conserva siete pendientes de migración y tres excepciones transitorias. Esto debe presentarse como una arquitectura en refactor incremental, no como Clean Architecture perfecta.

### 3. Calidad de ingeniería y CI

La matriz Python 3.11–3.14, CodeQL, auditoría de dependencias, compilación, pruebas E2E e inventario modular son evidencia fuerte de disciplina. El hecho de encontrar fallas de integración y corregirlas antes de fusionar también es positivo: los checks se usan como barrera real, no como insignia decorativa.

### 4. Producto con un problema específico

El producto une préstamos privados, participaciones de inversores y análisis de reposición de capital. F1 empieza a completar la economía cotidiana del usuario:
- margen libre declarado sin exigir carga de gastos;
- reserva líquida y parte protegida;
- escenario repetido de meses con menos margen;
- calendario de cobros contractuales de inversiones propias por fecha;
- hipótesis transparentes de demora de 30/60 días o no recepción en el horizonte.

En la última etapa, el calendario reutiliza `AnalisisFinancieroQuery.flujos_proyectados`; no replica las fórmulas de amortización ni modifica pagos, ledger o contratos. Los cobros no se suman al margen declarado para evitar doble contabilización. El presupuesto guiado, cobros externos y caja consolidada aún no están implementados.

### 5. Sesiones SQLite y operación local

PR #369 incorporó conexiones independientes por sesión Streamlit y una prueba de dos sesiones sobre un mismo archivo. PR #393 agregó la limpieza de claves privadas temporales de Mi espacio al terminar o invalidarse la autenticación, con regresiones unitarias y E2E. Son mejoras concretas de aislamiento en el modo local. No demuestran pagos financieros concurrentes con idempotencia, revisión obsoleta y rollback; esa aceptación sigue en [#159](https://github.com/JavierGrecco/prestamos_privados/issues/159).

## Valoración para un líder técnico

La pregunta correcta no es si el proyecto ya está terminado, sino qué demuestra sobre la capacidad de diseñar, construir, probar y gobernar software de negocio complejo.

| Dimensión | Valoración | Motivo |
|---|---:|---|
| Arquitectura y evolución modular | **7,8/10** | Capas identificables, composición controlada, cero ciclos; aún hay siete migraciones y tres excepciones |
| Integridad y modelado financiero | **8,4/10** | Decimal, ledger, auditoría, idempotencia, rollback y diferenciación de hechos/proyecciones |
| Ingeniería de pruebas y CI | **8,8/10** | 1.393 pruebas por versión en cuatro Python, E2E, CodeQL, auditoría e inventario |
| Diseño de producto y diferenciación | **7,9/10** | Dominio específico, reposición de capital y capacidad de pago con explicaciones |
| Usabilidad y aceptación funcional | **6,2/10** | Las pantallas existen y tienen E2E, pero faltan recorridos manuales completos y aceptación independiente |
| Preparación operativa/producción | **5,4/10** | Restore drill, pagos concurrentes, migraciones históricas, seguridad/governance y reglas abiertas |

**Atractivo como proyecto de portfolio para un líder técnico: 7,8/10.** Es una valoración cualitativa, no una garantía de contratación. Tiene suficiente profundidad para una conversación técnica: modelado de dinero, consistencia transaccional, migración incremental, compatibilidad, diseño de consultas, CI y decisiones explícitas de riesgo. Lo que resta puntos es que aún no se cerró el ciclo de aceptación real del producto.

**Preparación para producción: 5,4/10.** No debe confundirse con el puntaje de portfolio. Un líder puede valorar la calidad de ingeniería y, al mismo tiempo, rechazar una puesta en producción mientras falten las pruebas operativas y las decisiones financieras indicadas.

Para presentarlo en entrevistas conviene describirlo como un producto local en evolución, con un núcleo financiero trazable y una suite automatizada amplia. No afirmar que está terminado, desplegado como SaaS o habilitado para manejar dinero real sin supervisión.

## Brechas y riesgos abiertos

| Tema | Situación | Seguimiento |
|---|---|---|
| Aceptación del MVP | Sin aceptación manual integral reciente de préstamo y reposición | [#223](https://github.com/JavierGrecco/prestamos_privados/issues/223) |
| Reglas Legacy/V3 | Diferencias en mora y waterfall; Legacy sigue efectivo | [#145](https://github.com/JavierGrecco/prestamos_privados/issues/145) |
| Imputación por cuota | Tratamiento de arrastres históricos requiere decisión | [#332](https://github.com/JavierGrecco/prestamos_privados/issues/332) |
| Calendario contractual | Alta real limitada a mensual; autoridad por fechas no gobierna todo el recorrido | [#189](https://github.com/JavierGrecco/prestamos_privados/issues/189) |
| Carencia inicial | Simulación/base técnica, no operación integral | [#186](https://github.com/JavierGrecco/prestamos_privados/issues/186), [#192](https://github.com/JavierGrecco/prestamos_privados/issues/192) |
| Pagos concurrentes | Falta E2E financiero de idempotencia, revisión obsoleta y rollback | [#159](https://github.com/JavierGrecco/prestamos_privados/issues/159) |
| Backup y recuperación | Falta restore drill manual en otra ruta | [#374](https://github.com/JavierGrecco/prestamos_privados/issues/374) |
| Migraciones | Matriz histórica de upgrades no alcanza todavía el esquema actual v026 | [#156](https://github.com/JavierGrecco/prestamos_privados/issues/156) |
| HTML dinámico | Revisiones cubren patrones conocidos, no una garantía universal | [#158](https://github.com/JavierGrecco/prestamos_privados/issues/158) |
| Gobierno de `main` | Sin protección administrativa ni checks obligatorios configurados | [#157](https://github.com/JavierGrecco/prestamos_privados/issues/157) |
| Identidad online | Solo autenticación local; no es SaaS ni multiusuario remoto | [#137](https://github.com/JavierGrecco/prestamos_privados/issues/137) |
| Distribución | Sin licencia pública ni releases | Decisión de producto pendiente |

## Estado de GitHub y mantenimiento

Al integrar PR #395 no quedaron PRs abiertas ni ramas de trabajo. Permanecen exactamente `main` (`be63dc7`) y `archive/legacy-branches-2026-11`, el anclaje que conserva los 14 HEAD históricos. La limpieza de la rama integrada y el housekeeping post-merge fueron aprobados. La política recomendada sigue siendo una rama temporal a la vez, PR contra `main`, CI verde, squash merge y eliminación automática de la rama integrada.

La protección administrativa de `main` sigue pendiente. El flujo automatizado de limpieza no reemplaza la configuración de branch protection y required checks.

## Próximo orden de trabajo recomendado

1. **Cerrar aceptación del MVP #223:** ejecutar los dos recorridos completos desde UI con base de prueba limpia y registrar resultados, no abrir otra línea grande de funcionalidades.
2. Resolver decisiones contractuales Legacy/V3, calendario y arrastre con casos numéricos aprobados.
3. Ejecutar restore drill en una ruta distinta y E2E de pagos concurrentes.
4. Cerrar conciliación de saldos, ledger, posiciones e informes con un mismo corte.
5. Configurar protección de `main`, ampliar revisión HTML y completar upgrades históricos.
6. Retomar F1.2: cobros externos declarados y caja fechada consolidada solo después de definir cómo se deduplican contra el margen libre y contra los flujos internos.

## Alcance de esta revisión

La revisión de base corresponde a PR #384; los addenda verifican PR #393, PR #395 y el estado post-merge de `main`. No se ejecutó una aceptación manual en navegador, pentest externo, restore drill completo ni prueba financiera con datos productivos. Esos límites están reflejados en la valoración y no deben ocultarse en una presentación.
