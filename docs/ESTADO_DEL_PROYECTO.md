# Estado del proyecto y prioridades

**Corte técnico/documental:** 26 de noviembre de 2026 (hora Argentina).  
**Base de código auditada:** [`feb12a0`](https://github.com/JavierGrecco/prestamos_privados/commit/feb12a020dfd53e3fad9ceccda646e7e9065598e), posterior a la integración de PR #384.
**Corte de aceptación funcional:** la última evaluación manual documentada sigue siendo del 12 de octubre de 2026; esta actualización técnica no equivale a una nueva aceptación de producto.  
**Seguimiento:** [Issue #223 — MVP local P0](https://github.com/JavierGrecco/prestamos_privados/issues/223).  
**Documentos de referencia:** [Producto](PRODUCTO.md) · [Roadmap operativo](ROADMAP_MVP_LOCAL.md) · [Evaluación ejecutiva histórica](EVALUACION_EJECUTIVA_MVP_2026-10-12.md) · [Estado de modularización](ESTADO_MODULARIZACION.md) · [Registro de cambios](REGISTRO_DE_CAMBIOS.md).

## Resumen ejecutivo

Préstamos Privados tiene una base técnica seria e integrada: núcleo de préstamos y pagos, ledger y auditoría, superficies financieras personales, persistencia y reportes de planes de reposición, propuestas de correcciones auditables y controles importantes de atomicidad, migraciones y precisión.

Todavía **no se debe declarar el MVP local terminado ni listo para operar sin supervisión**. Los bloqueos principales son contractuales/temporales, la aceptación visual y funcional en la instalación local, la conciliación completa de posiciones/reportes, y la demostración operativa de backup/restauración y concurrencia desde la interfaz.

## Actualización técnica — 26 de noviembre de 2026

Desde la evaluación funcional de octubre se integraron mejoras de arquitectura, operación de sesiones, capacidad de pago personal y proyección fechada de cobros. PR #372 y #373 alinearon documentación; PR #382 y #384 incorporaron código funcional sin modificar contratos, pagos ni reglas económicas de préstamos.

- PR #354 incorporó una guarda de CI que impide introducir ciclos de importación detectados por el inventario modular.
- PR #356 y PR #359 retiraron las anotaciones concretas `BaseDatos` de las doce pantallas cubiertas por la guarda; el contexto de persistencia se trata como opaco en el límite de UI.
- PR #360 hizo idempotente la limpieza ante referencias eliminadas concurrentemente. PR #361 corrigió la dirección de comparación `branch...main`, agregó una regresión que protege el criterio `behind_by === 0` y actualizó `actions/github-script` a v9 (Node 24).
- PR #363 incorporó contratos de error de persistencia en aplicación y migró tres pantallas de UI y la fachada de pagos para capturar contratos, conservando los nombres públicos de excepciones SQLite.
- PR #365 inició la deprecación gradual del constructor histórico `ServicioPagos(db)`: conserva compatibilidad y emite `DeprecationWarning`; la fábrica oficial con siete colaboradores inyectados permanece sin advertencias.
- PR #367 trasladó la apertura, inspección e inicialización de SQLite desde `ui/app.py` a `infraestructura/composicion/apertura_base_datos.py`; la UI ya no importa `BaseDatos` ni el gestor de migraciones.
- PR #369 aisló las conexiones SQLite por sesión Streamlit con liberación del recurso y una prueba E2E de dos sesiones independientes sobre el mismo archivo.
- PR #372 alineó los documentos principales con el estado verificado y añadió un informe de revisión técnica; su alcance fue exclusivamente documental.
- PR #382 agregó reserva líquida protegida y escenarios de margen ajustado de 1–24 meses, temporales por sesión.
- PR #384 incorporó el calendario de cobros proyectados de inversiones propias por fecha, con escenarios de demora de 30/60 días o no recepción durante el horizonte; reutiliza `AnalisisFinancieroQuery` y no agrega esos flujos al margen declarado.
- La última validación de PR #384 inventarió 320 archivos Python, 1.712 importaciones, 308 cruces entre capas y 56 hallazgos: 7 pendientes de migración, 3 excepciones temporales documentadas y 46 usos de composición de borde. Se detectaron cero ciclos.

Estas mejoras reducen deuda técnica, pero no demuestran aceptación contractual, visual ni operativa del MVP.

## Evidencia de validación automatizada

**Inventario de arquitectura de la última validación disponible de PR #384:** 320 archivos Python analizados sin errores, 1.712 importaciones, 308 cruces entre capas y 56 hallazgos en 26 archivos: 7 pendientes de migración, 3 excepciones temporales documentadas y 46 usos de composición en los bordes permitidos. Se detectaron cero ciclos de importación. Los usos de composición son puntos de ensamblado clasificados, no 46 defectos.

**CI de PR #384 antes de su integración en `main`:**

- **1.372 pruebas aprobadas en cada versión de Python 3.11, 3.12, 3.13 y 3.14** en la validación de PR #387. Se verificó el resumen de cada job, no solo el estado global.
- Compilación, consistencia de dependencias e inventario modular aprobados.
- CodeQL y auditoría de dependencias aprobados.
- [Matriz de pruebas](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45904847625) · [Seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45904847569) · [PR #384](https://github.com/JavierGrecco/prestamos_privados/pull/384).

La evidencia corresponde al head de PR #384, que fue integrado mediante squash en `feb12a0`. No se presenta como una nueva aceptación manual ni como validación en una base productiva.

La cifra es por cada versión de Python, no una suma de cuatro suites diferentes. CI verde valida el estado automatizado del commit indicado, pero no prueba por sí mismo que una persona completó los recorridos en navegador ni que restauró una copia histórica.

## Evaluación y estimación funcional

Las cifras de esta tabla corresponden a la evaluación del 12 de octubre de 2026. No se recalcularon con los cambios de arquitectura de noviembre ni representan una medición actual hasta completar la aceptación manual pendiente.

| Medida | Estimación al 12/10/2026 | Cómo leerla |
|---|---:|---|
| Calidad técnica como proyecto en desarrollo | **7,0/10** | Separación por capas, controles de persistencia, trazabilidad, CI y pruebas amplias |
| Completitud funcional estimada | **65–70%** | Amplia base integrada; faltan cierres de extremo a extremo y aceptación |
| Preparación operativa para dinero real | **55–60%** | No equivale a autorización de producción; quedan pruebas contractuales y operativas |
| Esfuerzo restante del MVP local | **21–34 jornadas de ingeniería** | Estimación media-baja de confianza; depende de reglas aprobadas y defectos hallados |
| Tiempo orientativo | **4–7 semanas completas** o **6–10 semanas calendario** con dedicación parcial | No es una fecha prometida |
| Extensión opcional | **+2–4 jornadas** | Si la comparación frente al precio de contado del auto es requisito obligatorio del primer piloto |

Los puntajes y porcentajes son una evaluación técnica razonada, no una métrica automática, auditoría externa ni certificación financiera. La metodología y comparación con herramientas profesionales están en [Evaluación ejecutiva](EVALUACION_EJECUTIVA_MVP_2026-10-12.md).

## Qué está integrado en `main`

| Frente | Estado | Alcance confirmado |
|---|---|---|
| Núcleo de préstamos | Integrado | Alta, cronograma mensual, cuotas, pagos, mora, adelantos y distribución entre inversores |
| Registro contable | Integrado | Ledger, auditoría, imputaciones y trazabilidad de operaciones |
| Motor de pagos V3 | Integrado para adopción controlada | Preview, SOMBRA, preflight, feature flag y evidencia; Legacy sigue como autoridad operativa |
| M1–M7 | Integrado | Mi espacio, posición, planificación, escenarios, rendimiento, reportes y comparador |
| F1 — capacidad de pago personal | Parcialmente integrado | Margen mensual declarado, ahorro líquido protegido, escenario de meses ajustados y cobros de inversor fechados; sin presupuesto completo ni persistencia personal |
| Identidad local y capacidades N1–N3 | Integrado con límites | Modelo de sesión/capacidades; el modo local no equivale a autenticación online |
| Planes de reposición v022–v025 | Integrado | Snapshots/versiones, aportes, flujos, valuaciones declaradas, XIRR condicionada e informes Markdown/JSON/CSV |
| Propuestas de corrección v026 | Integrado | Historial y comparación de propuestas inmutables; no aplican cambios efectivos al original |
| Hardening PR #258 | Integrado | Idempotencia y concurrencia Legacy, validación de entradas, rollback de operaciones anidadas, barrera de migraciones, precisión Decimal y reglas HTML |
| Correcciones auditables PR #260 | Integrado | Propuesta con autorización, motivo, hash, idempotencia e historial |
| Calendario por fechas y carencia | Base técnica, no operativa completa | La autoridad temporal existe, pero no controla aún todo el recorrido contractual/pagos/reportes |

## Bloqueos y orden de prioridad

### P0 — Decisiones financieras contractuales

- [#145 — divergencias Legacy/V3](https://github.com/JavierGrecco/prestamos_privados/issues/145): documentar y aprobar metodología de mora e imputación para escenarios sensibles. Legacy sigue vigente hasta que exista decisión y evidencia suficientes.
- [#332 — imputaciones por cuota con arrastre Legacy](https://github.com/JavierGrecco/prestamos_privados/issues/332): sigue pendiente decidir la semántica de atribución por cuota y el tratamiento de hechos históricos antes de cambiar la regla.
- [#189 — amortización por fechas y convención](https://github.com/JavierGrecco/prestamos_privados/issues/189): definir el significado contractual de TNA/TEA para períodos regulares e irregulares, reglas de calendario, fin de mes y año bisiesto. La alta real sigue admitiendo solo `MENSUAL`.
- [#186](https://github.com/JavierGrecco/prestamos_privados/issues/186) y [#192](https://github.com/JavierGrecco/prestamos_privados/issues/192): carencia. No habilitarla para operaciones reales hasta integrar contrato, cuotas, pagos parciales, adelantos, mora, ledger y reportes.

### P1 — Aceptación de los dos recorridos de producto

- **Préstamo privado:** alta, revisión del contrato, cuotas, pagos totales/parciales, adelantos permitidos, mora, distribución, auditoría e informes.
- **Autocrédito/reposición:** crear/guardar/versionar/reabrir/exportar un plan; explicar capital a reponer + referencia USD + rendimiento objetivo/costo de oportunidad; conciliar los datos declarados con posiciones e informes sin doble contabilización.
- Registrar resultados, capturas o evidencia reproducible y defectos en [#223](https://github.com/JavierGrecco/prestamos_privados/issues/223).

### P2 — Operación segura y gobierno

- Completar la instalación/reinicio y el restore drill manual en una ruta distinta; verificar integridad, saldos, ledger y auditoría ([#374](https://github.com/JavierGrecco/prestamos_privados/issues/374)).
- Completar la matriz de upgrades históricos hasta el esquema v026 y verificar que no se alteren hechos económicos ([#156](https://github.com/JavierGrecco/prestamos_privados/issues/156)).
- PR #367 ya separó el arranque y las migraciones de la UI (#160); su integración no reemplaza las dos pruebas anteriores.
- Ejecutar E2E de dos sesiones UI con pagos concurrentes e idempotencia ([#159](https://github.com/JavierGrecco/prestamos_privados/issues/159)).
- Ampliar las pruebas de seguridad HTML ([#158](https://github.com/JavierGrecco/prestamos_privados/issues/158)).
- Configurar protección de rama y checks requeridos de GitHub ([#157](https://github.com/JavierGrecco/prestamos_privados/issues/157)).

### Evolución posterior del producto

El [issue #370](https://github.com/JavierGrecco/prestamos_privados/issues/370) coordina el diseño de la capacidad de operación financiera asistida. Incluye registro contextual con borrador y confirmación, consultas financieras de solo lectura y seguimiento de objetivos de reposición. Está clasificada como **Post-MVP**: no altera los bloqueos de #223 ni se presenta como una función implementada. El contrato está en [CAPACIDAD_OPERATIVA_ASISTIDA.md](CAPACIDAD_OPERATIVA_ASISTIDA.md).

El [issue #375](https://github.com/JavierGrecco/prestamos_privados/issues/375) define F1 — Finanzas personales y capacidad de pago. Ya están integrados el margen libre declarado, la reserva líquida protegida y los escenarios de margen reducido ([PR #379](https://github.com/JavierGrecco/prestamos_privados/pull/379) y [#382](https://github.com/JavierGrecco/prestamos_privados/pull/382)); PR #384 agrega cobros contractuales de inversor por fecha y pruebas de demora/no recepción. Siguen pendientes la cuenta guiada, registro de ingresos/gastos, cobros externos, conciliación de caja y evaluación de toda la secuencia de cuotas de una nueva propuesta. El diseño y límites están en [FINANZAS_PERSONALES_CAPACIDAD_PAGO.md](FINANZAS_PERSONALES_CAPACIDAD_PAGO.md). F1 sigue siendo Post-MVP y no desplaza #223.

### P3 — Entrega y aceptación

Una persona distinta de quien implementó el código instala el proyecto desde una copia limpia, completa los dos recorridos, verifica exportaciones y restaura un backup. Debe quedar un registro de aceptación, limitaciones conocidas y decisión de la comisión. Hasta entonces, #223 permanece abierto.

## Funciones que no deben anunciarse como terminadas

- La carencia inicial está simulada y tiene snapshots, pero aún no es un flujo contractual operativo completo.
- Las propuestas de corrección v026 no modifican saldos, XIRR ni reportes; la aplicación efectiva es una etapa diferente.
- Las convenciones no mensuales no se habilitan en altas reales hasta que calendario, pagos e informes compartan la misma autoridad.
- V3 no debe convertirse en motor efectivo por calendario ni por el número de pruebas: requiere resolución formal de divergencias y autorización basada en evidencia.
- La interfaz no ha recibido todavía aceptación visual/manual integral; los tests automatizados no sustituyen esa tarea.
- La restauración de una base histórica en otro archivo sigue pendiente de demostración operativa.
- El modo local no es una oferta de autenticación multiusuario remota.

## Gobierno de ramas y PRs

La política vigente mantiene `main` como única referencia estable, una sola rama de trabajo activa y PRs dirigidas a `main`. Las PR #359–#369 quedaron integradas mediante squash. PR #361 corrigió la comparación `branch...main`, PR #363 separó los contratos de error de persistencia, PR #365 inició la deprecación del constructor Legacy, PR #367 trasladó el ciclo de apertura SQLite a composición y PR #369 aisló las conexiones SQLite por sesión. La limpieza automática conserva las ramas históricas con commits únicos y no las elimina por antigüedad.

La comparación segura de ramas se documenta en [Flujo de trabajo Git](FLUJO_DE_TRABAJO_GIT.md). Tras integrar PR #386 no quedaron PRs abiertas. El inventario conserva **14 ramas históricas divergentes además de `main`**; no son ramas activas ni deben integrarse o borrarse en bloque porque conservan commits exclusivos. `main` todavía no tiene protección administrativa (#157).

Un cambio está **Integrado** solo si está en `main` y su CI pasó. Está **Aceptado** únicamente cuando además se completó la validación funcional/operativa que le corresponde.

## Documentos de referencia

- [Roadmap MVP local: fases, dependencias y criterios de salida](ROADMAP_MVP_LOCAL.md)
- [Descripción oficial y funciones del producto](PRODUCTO.md)
- [Capacidad de operación financiera asistida](CAPACIDAD_OPERATIVA_ASISTIDA.md)
- [Evaluación, nota, porcentajes y comparación profesional](EVALUACION_EJECUTIVA_MVP_2026-10-12.md)
- [Arquitectura](ARCHITECTURE.md)
- [Instalación local](INSTALACION_LOCAL.md)
- [Seguridad](../SECURITY.md)
- [Índice de documentación](INDEX.md)


## Actualización de rama estable y housekeeping — 26/11/2026

- PR [#386](https://github.com/JavierGrecco/prestamos_privados/pull/386) integró una validación acotada para retirar una rama cuyo único commit exclusivo estaba vacío y cuyo padre ya estaba contenido en `main`.
- El workflow [branch housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45907769283) eliminó `feature/m4-escenarios-planificacion-v2` y la rama temporal integrada. El inventario quedó en **15 referencias: `main` y 14 ramas históricas preservadas**.
- El CI posterior al merge del commit `860163b` aprobó **1.370 pruebas en cada Python 3.11, 3.12, 3.13 y 3.14**, además de CodeQL y auditoría de dependencias ([tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45907769153) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45907769135)).
- Las 14 referencias restantes tienen historia o contenido exclusivo; no se consideran ramas de trabajo activas y solo se rescatarán mediante comparación y adaptación individual desde una rama nueva basada en `main`.
- El inventario de modularidad del CI analizó 320 archivos Python sin errores de parseo; los hallazgos permanecen clasificados como pendientes de migración, excepciones temporales documentadas y bordes de composición, no como una lista homogénea de defectos.
