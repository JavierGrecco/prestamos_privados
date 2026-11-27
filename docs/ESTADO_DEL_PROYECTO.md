# Estado del proyecto y prioridades

**Corte técnico/documental:** 27 de noviembre de 2026 (hora Argentina).  
**Base de código auditada:** [7b5a714](https://github.com/JavierGrecco/prestamos_privados/commit/7b5a714fb5d8a081e2db52a3fa9db628b0fe0aa2), posterior a PR #406. La aceptación manual integral sigue pendiente.
**Corte de aceptación funcional:** la última evaluación manual documentada sigue siendo del 12 de octubre de 2026; esta actualización técnica no equivale a una nueva aceptación de producto.  
**Seguimiento:** [Issue #223 — MVP local P0](https://github.com/JavierGrecco/prestamos_privados/issues/223).  
**Documentos de referencia:** [Producto](PRODUCTO.md) · [Roadmap operativo](ROADMAP_MVP_LOCAL.md) · [Evaluación ejecutiva histórica](EVALUACION_EJECUTIVA_MVP_2026-10-12.md) · [Estado de modularización](ESTADO_MODULARIZACION.md) · [Registro de cambios](REGISTRO_DE_CAMBIOS.md).

## Resumen ejecutivo

Préstamos Privados tiene una base técnica seria e integrada: núcleo de préstamos y pagos, ledger y auditoría, superficies financieras personales, persistencia y reportes de planes de reposición, propuestas de correcciones auditables y controles importantes de atomicidad, migraciones y precisión.

Todavía **no se debe declarar el MVP local terminado ni listo para operar sin supervisión**. Los bloqueos principales son contractuales/temporales, la aceptación visual y funcional en la instalación local, la conciliación completa de posiciones/reportes, y la demostración operativa de backup/restauración y concurrencia desde la interfaz.

## Actualización técnica — PR #400, PR #402, PR #404 y PR #406, 27 de noviembre de 2026 (hora Argentina)

- PR #400 consolidó en una proyección temporal común los cobros contractuales del rol inversor y los externos declarados. Conserva origen y referencias, evita referencias repetidas y previene el doble conteo con el margen por defecto.
- PR #402 incorporó comparación del margen habitual/ajustado contra el cronograma completo generado por el simulador oficial. Permite 1–360 cuotas de sistemas francés/alemán con tasas TNA/TEA. Cada cuota mantiene su fecha e importe; la caja estresada utiliza los faltantes por vencimiento y cobros solo hasta los primeros 1–24 vencimientos elegidos.
- PR #404 distingue los cobros externos `DECLARADO` de aquellos con `REFERENCIA_DOCUMENTAL_DECLARADA`. En el segundo caso se exige una referencia breve, pero la aplicación no recibe, almacena ni verifica documentos ni solvencia del pagador. La categoría es declarativa y no aumenta la ponderación financiera del cobro.
- Las simulaciones continúan en ARS y en sesión; no crean préstamos ni pagos, ni modifican contratos, cuotas, ledger, auditoría, snapshots o persistencia de finanzas personales.
- PR #406 amplió el restore drill para ejecutar el entrypoint `ui/app.py` mediante `AppTest`, apuntando exclusivamente a la copia restaurada. Verifica el primer arranque, crea un ADMIN sintético en esa copia, abre una segunda sesión que reconoce la cuenta existente, vuelve a autenticar y consulta el préstamo, el pago y el ledger. También verifica que el bootstrap no modifique la base sintética original.
- Esta automatización no simula el cierre/reinicio de un proceso Streamlit real ni la inspección del navegador; #374 y la aceptación general #223 siguen abiertos hasta completar la prueba manual.
- La validación post-merge de PR #406 aprobó 1.420 pruebas por Python 3.11–3.14; CodeQL, `pip-audit` y branch housekeeping también aprobaron. Evidencia: [tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45937308452) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45937308462) · [housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45937308479).
- F1.2 permanece Post-MVP: la clasificación declarativa de cobros ya está integrada, pero no verifica documentos, solvencia ni recepción; también falta conciliar el cobro cuando el dinero se recibe. No desplaza la aceptación P0 de #223.


## Actualización técnica — 26 de noviembre de 2026

Desde la evaluación funcional de octubre se integraron mejoras de arquitectura, operación de sesiones, capacidad de pago personal, proyección fechada de cobros, rendimiento por operación, aislamiento de datos privados por sesión y desacoplamiento incremental de pagos. PR #372 y #373 alinearon documentación; PR #382, #384, #391 y #395 incorporaron mejoras de código sin cambiar las reglas económicas de préstamos. PR #392 y #394 actualizaron el estado documental; PR #393 corrigió la limpieza de datos personales temporales.

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
- PR #387 agregó un simulacro reproducible de restauración SQLite con base sintética, destino separado y verificación de integridad; es evidencia automatizada, no reemplaza la restauración manual desde una instalación independiente.
- PR #391 completó M5 por operación: rendimiento del inversor y costo del deudor por préstamo/rol, con XIRR, resultado real, USD cuando hay evidencia completa, detalle de movimientos y tratamiento histórico opt-in para préstamos cerrados. No modifica contratos, pagos, ledger ni proyecciones; no agrega migraciones.
- PR #393 eliminó las claves temporales `mi_espacio_*` al cerrar sesión, al invalidarse la autenticación y al entrar en estado no autenticado. Se agregaron pruebas unitarias y E2E para esas tres transiciones. No agrega persistencia ni altera SQLite, contratos, pagos o ledger.
- PR #395 tipó la unidad transaccional de `ServicioPagos` con `UnidadTrabajoRegistroPago` y trasladó la generación UUID v4 de correlación a aplicación, con inyección mediante `GeneradorCorrelacionPago`. No elimina el constructor histórico ni las siete construcciones internas de repositorios, que siguen pendientes de transición y revisión de consumidores.
- La validación post-merge de PR #395 inventarió 323 archivos Python, 1.740 importaciones, 315 cruces entre capas y 54 hallazgos: 7 construcciones pendientes, 1 excepción temporal documentada y 46 usos de composición de borde. Se detectaron cero ciclos.

Estas mejoras reducen deuda técnica, pero no demuestran aceptación contractual, visual ni operativa del MVP.

## Evidencia de validación automatizada

**CI post-merge de PR #395 sobre `main` (`be63dc7`):**

- **1.393 pruebas aprobadas en cada versión de Python 3.11, 3.12, 3.13 y 3.14**; los logs individuales confirman el mismo total por intérprete.
- Compilación, consistencia de dependencias y diff check aprobados. El inventario modular se ejecutó en Python 3.11; el workflow lo omite intencionalmente en las otras versiones.
- CodeQL, `pip-audit` y branch housekeeping aprobados.
- [Matriz de pruebas](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45917468532) · [Seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45917468526) · [Housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45917468545).

**Inventario de arquitectura post-merge:** 323 archivos Python analizados sin errores, 1.740 importaciones, 315 cruces entre capas y 54 hallazgos en 26 archivos: 7 construcciones pendientes de migración, 1 excepción temporal documentada y 46 usos de composición en los bordes permitidos. Se detectaron cero ciclos de importación. Los usos de composición son puntos de ensamblado clasificados, no 46 defectos.

**Inventario modular post-merge de PR #402:** 323 archivos Python analizados sin errores, 1.747 importaciones, 318 cruces entre capas, 54 hallazgos (7 pendientes de migración, 1 excepción temporal documentada y 46 usos de composición) y cero ciclos. La issue #270 sigue abierta; el CI no convierte esos 7 pendientes en deuda resuelta.

**Evidencia histórica de CI post-merge de PR #387 sobre `main` (`1192e5d3`):**

- **1.372 pruebas aprobadas en cada versión de Python 3.11, 3.12, 3.13 y 3.14**, confirmadas en los logs individuales.
- Compilación, consistencia de dependencias y diff check aprobados. El inventario modular analizó 321 archivos Python sin errores en el job ejecutado en Python 3.11; en las otras versiones ese paso está configurado como omitido.
- CodeQL, `pip-audit` y branch housekeeping aprobados.
- [Matriz de pruebas](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45909138022) · [Seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45909138013) · [Housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45909138016).

**Evidencia histórica de PR #384 antes de su integración:**

- **1.369 pruebas aprobadas en cada versión de Python 3.11, 3.12, 3.13 y 3.14** en el head de PR #384.
- Compilación, consistencia de dependencias, inventario modular, CodeQL y auditoría de dependencias aprobados.
- [Matriz de pruebas](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45904847625) · [Seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45904847569) · [PR #384](https://github.com/JavierGrecco/prestamos_privados/pull/384).

La cifra de 1.372 que aparece arriba corresponde al estado posterior de PR #387 en `main`, no a PR #384.

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
| F1 — capacidad de pago personal | Parcialmente integrado | Margen declarado, reserva protegida, cobros contractuales y externos por fecha y comparación de 1–360 cuotas; estrés de caja hasta 24 vencimientos, en ARS y sesión, sin presupuesto completo ni persistencia personal |
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

El [issue #375](https://github.com/JavierGrecco/prestamos_privados/issues/375) define F1 — Finanzas personales y capacidad de pago. Están integrados el margen libre declarado, la reserva protegida, la proyección temporal conjunta de cobros contractuales/externos (PR #400) y la comparación de todas las cuotas de una propuesta contra el margen (PR #402). La persona puede comparar 1–360 cuotas y estresar la caja sobre 1–24 vencimientos elegidos. Siguen pendientes la evidencia/calidad de cobros externos, la conciliación cuando se reciben, la cuenta guiada, el registro de ingresos/gastos y los presupuestos. El diseño y límites están en [FINANZAS_PERSONALES_CAPACIDAD_PAGO.md](FINANZAS_PERSONALES_CAPACIDAD_PAGO.md). F1 sigue siendo Post-MVP y no desplaza #223.

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

La comparación segura de ramas se documenta en [Flujo de trabajo Git](FLUJO_DE_TRABAJO_GIT.md). La consolidación conserva los 14 HEAD históricos en [archive/legacy-branches-2026-11](ARCHIVO_RAMAS_HISTORICAS.md), separado del árbol funcional de `main`. Tras integrar PR #395, el inventario quedó en exactamente dos referencias: `main` (`be63dc7`) y el anclaje histórico. No hay PR abiertas ni ramas de trabajo; housekeeping eliminó la rama integrada y aprobó el control. `main` todavía no tiene protección administrativa (#157).

Un cambio está **Integrado** solo si está en `main` y su CI pasó. Está **Aceptado** únicamente cuando además se completó la validación funcional/operativa que le corresponde.

## Documentos de referencia

- [Roadmap MVP local: fases, dependencias y criterios de salida](ROADMAP_MVP_LOCAL.md)
- [Descripción oficial y funciones del producto](PRODUCTO.md)
- [Capacidad de operación financiera asistida](CAPACIDAD_OPERATIVA_ASISTIDA.md)
- [Evaluación, nota, porcentajes y comparación profesional](EVALUACION_EJECUTIVA_MVP_2026-10-12.md)
- [Arquitectura](ARCHITECTURE.md)
- [Instalación local](INSTALACION_LOCAL.md)
- [Seguridad](../SECURITY.md)
- [Revisión de ramas históricas](REVISION_RAMAS_HISTORICAS_2026-11-26.md)
- [Archivo de ramas históricas](ARCHIVO_RAMAS_HISTORICAS.md)
- [Índice de documentación](INDEX.md)


## Actualización de rama estable y housekeeping — 26/11/2026

- PR [#386](https://github.com/JavierGrecco/prestamos_privados/pull/386) integró una validación acotada para retirar una rama cuyo único commit exclusivo estaba vacío y cuyo padre ya estaba contenido en `main`.
- En el corte de PR #386, el workflow [branch housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45907769283) eliminó `feature/m4-escenarios-planificacion-v2` y la rama temporal integrada. En aquel momento el inventario quedó en **15 referencias: `main` y 14 ramas históricas preservadas**; es un dato histórico, no el estado actual posterior a PR #393.
- El CI posterior al merge del commit `860163b` aprobó **1.370 pruebas en cada Python 3.11, 3.12, 3.13 y 3.14**, además de CodeQL y auditoría de dependencias ([tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45907769153) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45907769135)).
- Las 14 referencias restantes tienen historia o contenido exclusivo; no se consideran ramas de trabajo activas y solo se rescatarán mediante comparación y adaptación individual desde una rama nueva basada en `main`.
- El inventario de modularidad del CI analizó 320 archivos Python sin errores de parseo; los hallazgos permanecen clasificados como pendientes de migración, excepciones temporales documentadas y bordes de composición, no como una lista homogénea de defectos.
