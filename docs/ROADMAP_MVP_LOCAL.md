# Hoja de ruta de implementación — MVP local

**Corte técnico/documental:** 27 de noviembre de 2026 (hora Argentina)  
**Base de código actual:** [58002ca](https://github.com/JavierGrecco/prestamos_privados/commit/58002cab249fd76c00b0ad576a4ce9d6c48de041), posterior a PR #427. La aceptación funcional manual integral sigue siendo la del 12/10/2026.
**Corte de aceptación funcional:** 12 de octubre de 2026; no se ha repetido una aceptación manual integral desde esa fecha.  
**Base funcional histórica:** `b9e81ff5ab810dfabe2c2ec4f6e59ca3fa7eba52` (PR #258 y #260)  
**Seguimiento coordinador:** [Issue #223 — MVP local P0](https://github.com/JavierGrecco/prestamos_privados/issues/223)  
**Evaluación ejecutiva histórica:** [EVALUACION_EJECUTIVA_MVP_2026-10-12.md](EVALUACION_EJECUTIVA_MVP_2026-10-12.md) · **Estado técnico actual:** [Estado del proyecto](ESTADO_DEL_PROYECTO.md) · **Descripción del producto:** [PRODUCTO.md](PRODUCTO.md) · **Capacidad futura:** [Operación financiera asistida](CAPACIDAD_OPERATIVA_ASISTIDA.md) · **Historial:** [Registro de cambios](REGISTRO_DE_CAMBIOS.md)

> **Este es el documento operativo principal para decidir el orden del trabajo y comprobar cuándo una fase está terminada.** El issue #223 debe reflejar su resumen y enlazar la evidencia. `ROADMAP.md` conserva la historia de los programas técnicos anteriores; no se debe usar como un segundo tablero del MVP.

## Addendum técnico — PR #427, 27/11/2026

- Se añadieron encabezados semánticos al nombre del producto y a los grupos de navegación.
- La prueba Chromium ejecuta Streamlit real con SQLite sintética vacía y una cuenta ADMIN temporal; autentica, recorre el menú con Tab, verifica foco visible y activa Mi espacio con Enter.
- Se mide el desbordamiento horizontal del documento, la aplicación y el contenedor a 1440, 1024, 768 y 390 px.
- La prueba encontró un desbordamiento real a 768 px provocado por las columnas proporcionales fijas de la cabecera (543 px de contenido frente a 468 px disponibles). Se reemplazaron por contenedores horizontales adaptables que permiten wrap. La prueba corrigió y aprobó en Chromium.
- CI post-merge: **1.446 pruebas aprobadas + 4 omitidas** en cada Python 3.11–3.14; Chromium 4/4; CodeQL, `pip-audit` y branch housekeeping aprobados ([tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/46030197642) · [browser](https://github.com/JavierGrecco/prestamos_privados/actions/runs/46030197638) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/46030197724) · [housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/46030197602)).
- **Límite:** D4 (#177) permanece abierto hasta realizar inspección visual manual en la instalación real, con pantallas pobladas, widgets y diferentes temas/dispositivos. Chromium cubre una base vacía, menú y Mi espacio; no sustituye lector de pantalla ni aceptación humana.

## Addendum técnico — PR #422, 27/11/2026

- Se agregó aceptación Chromium para el restore drill: el test ejecuta backup/restauración sintéticos, abre la copia con un proceso real de Streamlit y consulta la evidencia del pago.
- Detiene el primer proceso, arranca otro contra el mismo archivo restaurado y vuelve a consultar el mismo pago desde una sesión nueva de Chromium.
- Verifica que no se dupliquen pagos, que el ledger siga cuadrado y que el archivo de origen conserve su SHA-256 y no reciba el usuario ADMIN creado en la copia.
- CI: 1.442 aprobadas + 3 omitidas en cada Python 3.11–3.14; Chromium 3/3 (XSS, concurrencia y restore/reinicio); CodeQL y `pip-audit` aprobados.
- **Límite:** #374 permanece abierto hasta realizar la aceptación manual local y registrar inspección visual/operativa. La automatización no prueba recuperación ante pérdida física, almacenamiento externo ni RTO/RPO.

## Addendum técnico — PR #420, 27/11/2026

- Se amplió la aceptación XSS en Chromium: el historial auditable de pagos ahora cubre nota, motivo de anulación, medio, referencia y usuario que registró el movimiento, además de los campos nombre/destino ya cubiertos en Mi espacio.
- La fila de pago del escenario es sintética y anulada, insertada directamente en SQLite temporal. La prueba no ejecuta el caso de uso financiero ni modifica ledger, auditoría, contratos o migraciones.
- CI de PR #420: 1.442 aprobadas + 2 omitidas en cada Python 3.11–3.14; Chromium 2/2; CodeQL, `pip check` y `pip-audit` aprobados ([matriz](https://github.com/JavierGrecco/prestamos_privados/actions/runs/46019647645) · [Chromium](https://github.com/JavierGrecco/prestamos_privados/actions/runs/46019647653) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/46019647564)).
- Integrado por squash en [42ee3e8](https://github.com/JavierGrecco/prestamos_privados/commit/42ee3e8770d918226a17a7a48ed1a946b5f5d55a).
- **Límite:** #158 sigue abierto para revisión de helpers/atributos indirectos, otras pantallas y aceptación manual ampliada. No se declara una auditoría universal de XSS ni se modifica la condición de aceptación del MVP en #223.

## Addendum técnico — PR #418, 27/11/2026

- En Mi espacio, un cobro externo declarado pendiente puede marcarse como recibido. Si sigue disponible y no estaba incluido en el margen mensual, se agrega a la reserva líquida de la sesión; si ya fue utilizado o ya estaba incluido, no se duplica.
- El cobro recibido sale de la proyección futura, conserva la fecha de recepción declarada e invalida el cálculo de capacidad anterior. Los cambios siguen en sesión y no crean movimientos financieros persistidos.
- CI de PR #418: 1.442 aprobadas + 2 omitidas en cada Python 3.11–3.14, sin advertencias; Chromium 2/2; CodeQL y auditoría de dependencias aprobados.
- **Límite Post-MVP:** no se verifica el cobro ni se implementa persistencia privada/conciliación bancaria. La aceptación coordinadora #223 no se declara completada.

## Addendum técnico — PR #416 y #417, 27/11/2026

- PR #416 refuerza la validación de HTML dinámico: whitelist de clases CSS y bloqueo de interpolaciones en URLs, estilos y handlers activos.
- PR #417 agrega dos sesiones Chromium reales contra el mismo proceso Streamlit y la misma SQLite sintética. La segunda sesión no puede confirmar un preview obsoleto hasta actualizar y revisar el cálculo.
- CI validado: 1.438 aprobadas + 2 omitidas por cada Python 3.11–3.14; 2/2 pruebas Chromium; CodeQL y auditoría de dependencias aprobados. Los workflows post-merge de main también aprobaron.
- **Límites:** la automatización no reemplaza la aceptación manual de dos sesiones (#159), ni el restore drill manual (#374). La protección administrativa de main sigue pendiente (#157). Legacy continúa como autoridad efectiva.
- F1.2 permanece Post-MVP; sus datos siguen en sesión. La aceptación de #223 no se declara completada.

## Addendum técnico — PR #415, 27/11/2026

- Se incorpora una aceptación XSS de navegador real mediante Chromium y Streamlit en loopback, sobre SQLite sintético con nombre/destino hostiles.
- Playwright queda aislado en `requirements-browser.txt`; el workflow propio instala Chromium y audita todas sus dependencias antes de ejecutar la prueba.
- Validación PR: 1.433 pruebas + 1 omitida por cada Python 3.11–3.14, CodeQL/auditorías verdes y 1 prueba Chromium aprobada ([tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/46007688045) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/46007688049) · [Chromium](https://github.com/JavierGrecco/prestamos_privados/actions/runs/46007687941)).
- **Límite:** la prueba cubre un único recorrido/campos. #158 sigue abierto para revisar notas, motivos, referencias, helpers/atributos indirectos y aceptación manual ampliada.

## Addendum técnico — PR #413 y #414, 27/11/2026

- PR #413 amplía la guarda estática de HTML: alias, colecciones, comprensiones, `.join()`, transformaciones de cadena y atributos `class`/`style`.
- CI post-merge: 1.432 pruebas por cada Python 3.11–3.14; CodeQL, auditoría de dependencias y housekeeping aprobados ([tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45945035822) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45945035784) · [housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45945035796)).
- PR #414 incorpora un E2E AppTest que inyecta texto hostil en registros sintéticos y verifica el escape en Resumen y Mi espacio.
- **Límite:** AppTest verifica el contenido entregado al renderizador, no el DOM de un navegador real. #158 sigue abierto hasta esa aceptación manual y la revisión de helpers/atributos indirectos.

## Addendum técnico — PR #411, 27/11/2026

- Se cerró #156 con una regresión de base financiera sintética v009→v026 ejecutada mediante el gestor real.
- La prueba compara los campos preexistentes de préstamo, cuotas, pagos, imputaciones, participaciones, saldos/ledger y auditoría; las columnas técnicas nuevas quedan fuera del snapshot original y se verifican por separado cuando corresponda.
- Se prueba el backfill de política de pago para fechas cubiertas y la conservación de `NULL` cuando no hay evidencia de vigencia, además de historial continuo, FK, integridad y segunda ejecución idempotente.
- Las rutas v020→v026 y v025→v026 cuentan con regresiones complementarias.
- CI post-merge: 1.426 pruebas por cada Python 3.11–3.14; CodeQL, auditoría de dependencias y housekeeping aprobados ([tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45943273392) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45943273492) · [housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45943273357)).
- **Límite:** #156 certifica los fixtures sintéticos versionados; no autoriza actualizar bases externas sin inspección de historial y backup independiente.

## Addendum técnico — PR #409, 27/11/2026

- Se integró revisión optimista en el registro de pagos Legacy/SOMBRA: las intenciones nuevas con preview obsoleto se rechazan dentro de la transacción de escritura.
- La repetición de una misma intención se resuelve antes de validar la revisión y conserva su clave/huella; una intención diferente no puede usar un preview vencido.
- La revisión del préstamo se incrementa en la misma transacción que pago, imputaciones, cuotas, ledger y auditoría. Se añadieron pruebas E2E de dos sesiones, retry idempotente tras avanzar la revisión y rollback inducido.
- SOMBRA vuelve a transmitir la fecha valor al escritor Legacy efectivo.
- CI post-merge de `main`: 1.425 pruebas aprobadas en cada Python 3.11–3.14; CodeQL, auditoría de dependencias y housekeeping aprobados ([tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45941966289) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45941966209) · [housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45941966201)).
- **Límite:** las pruebas automatizadas ya cubren los escenarios de concurrencia financiera, pero no sustituyen la aceptación manual en navegador/sesiones reales. #159 permanece abierto hasta registrar esa evidencia; #223 sigue siendo el coordinador de aceptación del MVP.

## Addendum técnico anterior — PR #406, 27/11/2026

- El restore drill ya no se limita a abrir la copia restaurada desde infraestructura: el E2E apunta `PRESTAMOS_DB_PATH` al archivo restaurado y ejecuta el entrypoint real de Streamlit mediante `AppTest`.
- La prueba comprueba el arranque inicial, crea una cuenta ADMIN sintética solo en la copia, abre un contexto nuevo que encuentra esa cuenta y muestra login, autentica la sesión y vuelve a consultar préstamo, pago y ledger.
- Verifica que el alta de prueba no haya creado usuarios en la base sintética original.
- CI post-merge: 1.420 pruebas aprobadas en cada Python 3.11–3.14; CodeQL, `pip-audit` y housekeeping aprobados ([tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45937308452) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45937308462) · [housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45937308479)).
- **Límite:** `AppTest` no equivale al cierre y reinicio de un proceso Streamlit real ni a una inspección en navegador. #374 permanece abierto hasta completar esos pasos manuales; #223 continúa siendo el coordinador P0.


## Addendum técnico histórico — PR #404, 27/11/2026

- Se clasifican los cobros externos como `DECLARADO` o `REFERENCIA_DOCUMENTAL_DECLARADA`; esta última categoría requiere una referencia textual identificable.
- La referencia no es un documento adjunto ni verificado: no acredita autenticidad, solvencia del pagador ni recepción efectiva, y ambas categorías mantienen igual peso en la proyección.
- Los cobros continúan en ARS y en sesión. No se crea una operación financiera real ni se modifica SQLite, el ledger, la auditoría o los contratos.
- CI post-merge: 1.420 pruebas por Python 3.11–3.14; CodeQL, `pip-audit` y branch housekeeping aprobados ([tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45934267143) · [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45934267125) · [housekeeping](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45934267141)).
- La aceptación manual integral continúa pendiente; PR #404 no modifica las prioridades de #223 ni convierte F1.2 en parte del MVP.

## Addendum Post-MVP — Finanzas personales #375/#381, 26/11/2026

Las entregas de capacidad de pago personal no cambian las fases, prioridades ni condiciones de salida del MVP local:

- PR #400 integra cobros contractuales del rol inversor con cobros externos declarados en una proyección temporal fechada.
- PR #402 permite comparar el margen contra cada una de las 1–360 cuotas de una propuesta generada por el simulador oficial (sistemas francés/alemán, TNA/TEA). El escenario de consumo de reserva se mantiene en 1–24 vencimientos elegidos.
- Todo sigue en ARS y en sesión: no hay persistencia personal, pagos reales ni cambios a ledger/contratos. La calidad de evidencia externa y la conciliación al recibir siguen pendientes.
- F1/F1.2 continúa Post-MVP y no bloquea #223. La revisión del MVP y sus estimaciones históricas deben evaluarse por separado.


## 1. Estado real a la fecha

La base funcional está integrada en `main`; el trabajo pendiente ya no se mide por cantidad de pantallas o clases, sino por recorridos completos, reglas financieras acordadas y aceptación de operación local.

La consolidación del [PR #258](https://github.com/JavierGrecco/prestamos_privados/pull/258) está en la historia de `main`. Las correcciones auditables de planes internos quedaron integradas por el [PR #260](https://github.com/JavierGrecco/prestamos_privados/pull/260), en el commit de referencia indicado arriba.

**Evidencia histórica de PR #384 (corte anterior; no representa el HEAD actual):**
- **1.372 pruebas aprobadas en cada una de Python 3.11, 3.12, 3.13 y 3.14** en la validación de PR #387.
- Compilación, consistencia de dependencias e inventario modular aprobados.
- CodeQL y auditoría de dependencias aprobados.
- Inventario: 320 archivos Python, 1.712 importaciones, 308 cruces entre capas, 56 hallazgos clasificados y cero ciclos.
- [Matriz de pruebas](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45904847625) · [Controles de seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/45904847569) · [PR #384](https://github.com/JavierGrecco/prestamos_privados/pull/384)

Las estimaciones de **7,0/10**, **65–70%**, **55–60%** y **21–34 jornadas** proceden de la evaluación funcional del 12 de octubre; siguen siendo referencias históricas y no mediciones actuales. La valoración técnica actualizada y sus límites están en [REVISION_TECNICA_2026-11-26.md](REVISION_TECNICA_2026-11-26.md).

Esto confirma la suite automatizada del commit señalado. **No equivale** a aceptación visual manual, prueba de instalación limpia ni simulacro de restauración de una base histórica.

### Resumen por frente

| Frente | Estado verificable | Lo que falta para cerrarlo |
|---|---|---|
| Núcleo financiero y seguridad de persistencia | **Integrado; CI verde** | Mantener regresiones y aceptar los recorridos de producto |
| Préstamo real y calendario | **Parcial / bloqueado por decisión contractual** | La ruta operativa de alta solo admite `MENSUAL`; incorporar la autoridad temporal por fechas sin recalcular préstamos históricos |
| Carencia inicial | **Base técnica integrada; no operativa de punta a punta** | Acordar contrato y devengamiento; conectar snapshot, cronograma, pagos, mora, ledger e informes |
| Autocrédito/reposición | **Persistencia y reportes de plan integrados** | Aceptar el recorrido manual; conectar posición e informes sin doble contabilización |
| Correcciones auditables v026 | **Propuestas integradas** | Las propuestas no aplican cambios a los hechos; definir y probar un proceso de corrección efectiva en fase separada |
| Interfaz y navegación | **Implementadas; aceptación manual pendiente** | Probar los dos recorridos con instalación local y registrar resultados |
| Backup, actualización y recuperación | **Controles y drill sintético automatizado; aceptación manual pendiente** | Ejecutar fixture con préstamo/pago, restaurar en otra ruta, comparar esquema y hechos económicos, abrir manualmente la copia y verificar saldos, ledger, auditoría y reportes |
| Concurrencia de sesiones Streamlit | **Hardening y pruebas financieras E2E automatizadas integradas** | Aceptación manual en navegador/sesiones reales y registro de evidencia en #159 |
| Adopción de V3 | **No autorizada para cut-over** | Resolver divergencias financieras en #145 y aprobar evidencia; Legacy sigue siendo autoridad operativa |
| Protección de `main` | **Pendiente de configuración administrativa** | Configurar protección de rama y checks requeridos según #157 |

### Reglas para evitar falsas señales de avance

- Una migración, pantalla, clase o prueba aislada no cierra un recorrido funcional.
- El CI verde certifica lo que ejecutan esos checks; no certifica una prueba visual o una recuperación manual.
- La etiqueta visible de 30/360 ya identifica la convención como **30E/360 ISDA (ajuste de fin de mes)** y explica la excepción del vencimiento final en febrero. No se deben cambiar importes solo por cambiar el texto.
- Aunque el cálculo por fechas ya existe, los préstamos reales solo pueden crearse con convención `MENSUAL` mientras alta, pagos e informes no compartan la misma autoridad temporal.
- Las propuestas de corrección v026 son inmutables y trazables, pero no cambian el original, saldos, XIRR ni informes.
- Legacy continúa siendo el motor efectivo. No hacer cut-over de V3 por calendario ni por tener más pruebas.

## 2. Estimación para terminar el MVP local

**Última estimación publicada: 21–34 jornadas de ingeniería (12/10/2026, histórica).** No se ha recalculado después de las mejoras técnicas de noviembre ni de una nueva aceptación manual. No debe presentarse como una previsión vigente; primero hay que ejecutar los recorridos pendientes y revisar las decisiones contractuales.

Como referencia histórica del 12/10/2026, esa banda equivalía a **4–7 semanas de dedicación completa** o **6–10 semanas calendario** con dedicación parcial. Si incluir la comparación/cobertura contra el precio de contado del vehículo fuera obligatorio para el primer piloto, el cálculo anterior sumaba **2–4 jornadas**. Ninguna de estas cifras fue reestimada al 26/11/2026.

La evaluación ejecutiva del 12/10/2026 publicó rangos de **65–70% de avance funcional** y **55–60% de preparación operativa**. Son estimaciones históricas y no se recalcularon después de los cambios de noviembre. No deben interpretarse como mediciones actuales ni como autorización para operar con dinero real.

| Fase | Esfuerzo restante | Estado | Referencias |
|---|---:|---|---|
| 0. Decisiones financieras y alcance | 2–3 jornadas | **En curso / bloqueante** | [#145](https://github.com/JavierGrecco/prestamos_privados/issues/145), [#189](https://github.com/JavierGrecco/prestamos_privados/issues/189), [#186](https://github.com/JavierGrecco/prestamos_privados/issues/186) |
| 1. Contrato y calendario del préstamo | 4–6 jornadas | **Pendiente de fase 0** | [#189](https://github.com/JavierGrecco/prestamos_privados/issues/189), [#192](https://github.com/JavierGrecco/prestamos_privados/issues/192) |
| 2. Autocrédito y reposición propios | 2–4 jornadas | **Integrado parcialmente; aceptación/conexión pendiente** | [#194](https://github.com/JavierGrecco/prestamos_privados/issues/194), [#202](https://github.com/JavierGrecco/prestamos_privados/issues/202), [#204](https://github.com/JavierGrecco/prestamos_privados/issues/204) |
| 3. Dos recorridos visuales completos | 3–5 jornadas | **Pendiente de aceptación manual** | [#179](https://github.com/JavierGrecco/prestamos_privados/issues/179), [#223](https://github.com/JavierGrecco/prestamos_privados/issues/223) |
| 4. Pagos, posiciones e informes integrados | 3–5 jornadas | **Parcial; reconciliación pendiente** | [#223](https://github.com/JavierGrecco/prestamos_privados/issues/223), [#201](https://github.com/JavierGrecco/prestamos_privados/issues/201), [#206](https://github.com/JavierGrecco/prestamos_privados/issues/206) |
| 5. Operación local, seguridad y recuperación | 4–6 jornadas | **Parcial; AppTest de restore y E2E financiero concurrente integrados; faltan reinicio manual y aceptación en navegador** | [#157](https://github.com/JavierGrecco/prestamos_privados/issues/157), [#158](https://github.com/JavierGrecco/prestamos_privados/issues/158), [#159](https://github.com/JavierGrecco/prestamos_privados/issues/159), [#374](https://github.com/JavierGrecco/prestamos_privados/issues/374) |
| 6. Aceptación y entrega local | 3–5 jornadas | **Pendiente** | [#179](https://github.com/JavierGrecco/prestamos_privados/issues/179), [#223](https://github.com/JavierGrecco/prestamos_privados/issues/223) |

La suma de las bandas por fase es 21–34 jornadas; puede haber solapamiento parcial entre actividades, pero no se descuentan días por tareas que aún no hayan sido aceptadas.

## 3. Fases, entregables y criterios de salida

### Fase 0 — Cerrar reglas y alcance

**Objetivo:** que una sola regla financiera aprobada gobierne cada cálculo; que no haya diferencias implícitas entre simulador, contrato y pagos.

**Entregables:**
- Especificación legible de modalidades incluidas en el primer MVP: TNA/TEA, cuotas mensuales, mora, pago parcial, adelanto RAI/RNI y waterfall interés/capital.
- Casos numéricos esperados, con fechas e importes, que sirvan de referencia para las pruebas.
- Decisión explícita sobre Legacy/V3: Legacy continúa como autoridad mientras #145 esté abierto.
- Decisión de calendario: qué representa cada convención y cuáles quedan habilitadas en préstamos reales.
- Decisión de carencia: modalidades permitidas, interés durante la espera, destino del interés no cobrado, fecha del primer vencimiento y prohibición de capitalización accidental.
- Confirmación de que el plan propio de reposición no crea por sí solo una deuda legal contra la misma persona.

**Sale de fase cuando:** las decisiones, ejemplos numéricos y exclusiones estén documentados y aceptados. No requiere cambiar cálculos en la misma entrega.

### Fase 1 — Contrato real y calendario

**Objetivo:** que lo que el usuario confirma en la UI sea exactamente lo que se persiste y luego se utiliza al calcular deuda y pagos.

**Entregables:**
- Una autoridad temporal única para modalidad, calendario y convención de días.
- Comparación de regresión contra el motor Legacy en los casos mensuales actuales.
- Casos de fin de mes, febrero, año bisiesto y períodos irregulares.
- Snapshot contractual persistente conectado al alta solo para modalidades aprobadas.
- Igualdad entre la simulación que se muestra antes de confirmar y el calendario guardado.
- Conservación de importes y fechas de préstamos históricos; no recalcular registros existentes de forma automática.

**Sale de fase cuando:** el préstamo real puede crearse, consultarse y cobrarse con el mismo contrato/calendario, y las diferencias se explican por casos numéricos aprobados. La carencia no se habilita antes de cerrar el E2E descrito en la Fase 3.

### Fase 2 — Autocrédito y reposición de capital

**Objetivo económico obligatorio:** **reponer capital + conservar poder adquisitivo en USD + añadir un rendimiento objetivo/costo de oportunidad**, sin presentar proyecciones como ganancias realizadas.

**Entregables:**
- Crear, guardar, versionar, reabrir y cerrar un plan.
- Separar capital reservado, aportes, flujos de inversión, costos externos y valuaciones declaradas.
- Mostrar cotizaciones, fuentes, fechas y naturaleza observada/declarada/proyectada.
- Diferenciar resultado realizado, valuación no realizada, supuesto de benchmark y escenario.
- Integrar los datos aceptados a posiciones e informes sin contabilizar dos veces aportes, rescates o proyecciones.
- Definir cómo se autoriza/aplica una corrección efectiva sobre los registros para los que v026 hoy solo conserva propuestas. Preferir una nueva versión o ajuste trazable; nunca sobrescribir silenciosamente el original ni reescribir informes históricos sin evidencia.

**Sale de fase cuando:** el plan se entiende desde la UI, se puede reabrir y explicar; los reportes reconcilian sus hechos y sus hipótesis; y el rendimiento objetivo no se muestra como rentabilidad realizada.

### Fase 3 — Recorridos visuales end-to-end

**A. Préstamo privado real**
- Crear un préstamo desde la UI con deudor e inversor(es), aportes conciliados y condiciones claras.
- Revisar y confirmar cuota, fechas, tasa, costo total y condiciones.
- Registrar pago total, parcial, vencido y adelanto según las reglas aprobadas.
- Comprobar saldo, mora, waterfall, participación, ledger y auditoría.
- Consultar el detalle e informe desde las perspectivas de deudor e inversor.

**B. Plan interno de reposición**
- Crear y guardar un plan, registrar aportes y datos de inversión declarados, reabrir versiones y descargar informes.
- Distinguir capital a reponer, referencia USD, objetivo de rendimiento, supuesto de inversión y brecha.
- Comparar valor futuro del capital alternativo contra cuotas/aportes reinvertidos con fechas compatibles y fuentes identificadas.

**Sale de fase cuando:** una persona puede completar ambas rutas sin scripts, SQL manual ni asistencia del desarrollador; el test manual queda registrado, incluyendo los fallos encontrados y su resolución.

### Fase 4 — Posiciones e informes

**Objetivo:** que el detalle por operación, la posición personal y las exportaciones hablen el mismo idioma.

**Entregables:**
- Corte de fecha consistente para deuda, pagos, aportes, flujos y valuaciones.
- Reconciliación de movimientos a ledger y auditoría.
- Diferenciar hechos registrados, datos declarados por el usuario, estimaciones y proyecciones.
- Verificación de que un pago, corrección propuesta, aporte o rescate no duplique capital o resultado.

**Sale de fase cuando:** las sumas de control de pantalla, reporte y ledger concuerdan con las mismas fechas y supuestos.

### Fase 5 — Operación local segura

**Entregables:**
- Instalación limpia, creación inicial del administrador, reinicio y persistencia.
- Backup íntegro de una base con datos de prueba; restauración en otra ruta; verificación de integridad, cantidades de registros, saldo, ledger y auditoría.
- Actualización de una copia histórica con historial válido; rechazo inmutable de historiales incompletos/desconocidos.
- La automatización ya cubre dos sesiones Streamlit, idempotencia, bloqueo por revisión obsoleta y ausencia de duplicación (PR #409). Completar además la aceptación manual desde dos sesiones reales/navegador y registrar evidencia en #159.
- Revisión de HTML dinámico y controles de seguridad.
- Configuración administrativa de la protección de `main` y checks obligatorios, si los permisos de GitHub lo permiten.

**Sale de fase cuando:** la recuperación se demuestra en una copia distinta, los errores de operación tienen salida segura y no quedan riesgos críticos abiertos sin decisión escrita.

### Fase 6 — Aceptación y entrega

**Entregables:**
- Ejecución de la guía desde una copia limpia del repositorio.
- Caso de préstamo privado y caso de reposición ejecutados en la UI.
- Evidencia de instalación, reinicio, consulta de saldos, exportación y restauración.
- Lista de defectos conocidos, decisiones financieras, limitaciones y alcance post-MVP.
- Revisión de la comisión y aceptación formal del alcance.

**Sale de fase cuando:** no hay defectos financieros críticos abiertos, todos los criterios obligatorios se demostraron y la comisión acepta la entrega.

## 4. Orden de trabajo inmediato

1. **No cambiar reglas económicas por intuición.** Registrar ejemplos numéricos y cerrar #145/#189/#192.
2. **Hacer una aceptación local de la base ya integrada.** Instalación, arranque, préstamo mensual de prueba, pago total/parcial, plan interno, exportación y reinicio; anotar resultados en #223.
3. **Completar un drill backup/restore.** Usar una base de prueba, no datos productivos, y restaurar en un archivo nuevo.
4. **Unificar calendario contractual.** Implementar la autoridad por fechas con pruebas de compatibilidad y sin recalcular préstamos históricos.
5. **Completar el E2E de carencia.** Solo tras decisiones aprobadas y validación de contrato, calendario, cuotas, pagos, mora, ledger y reportes.
6. **Conectar plan, posiciones y reportes.** Evitar doble contabilización y separar realizado/no realizado/proyectado.
7. **Cerrar las brechas de sesión y gobernanza.** E2E multi-sesión y protección administrativa de `main`.
8. **Registrar la aceptación final** y recién entonces cerrar #223.

## 5. Regla de seguimiento en GitHub

- Este documento fija fases, dependencias, estimación y criterios de salida.
- [Issue #223](https://github.com/JavierGrecco/prestamos_privados/issues/223) lleva el estado ejecutivo actual, las casillas de aceptación y enlaces a evidencia; no debe conservar estimaciones anteriores como si fueran actuales.
- Los issues técnicos abiertos (#145, #157–#160, #179, #186, #189, #192, #194, #201, #202, #204, #206) guardan detalle por tema. El issue #156 se cerró mediante PR #411.
- Cada PR debe indicar fase e issue, alcance de producto, reglas financieras que cambia/no cambia, pruebas, CI y aceptación manual pendiente.
- Cada cambio de fase debe actualizar `docs/REGISTRO_DE_CAMBIOS.md` y la fecha de corte. No repetir el estado completo en varios documentos.
- Los estados permitidos son: **Integrado**, **En curso**, **Bloqueado por decisión**, **Pendiente de aceptación** y **Post-MVP**.
- Una tarea pasa a **Integrado** cuando está en `main` con CI aprobado; pasa a **Aceptado** únicamente cuando también cumple la aceptación funcional que corresponda.

## 6. Fuera del MVP local

Se mantienen fuera del camino crítico el despliegue por Internet, identidad online, operación multiusuario remota, conciliación automática con brokers/mercados, órdenes de inversión y modelado fiscal/instrumental completo. La cobertura comparada contra el precio contado del vehículo se suma al primer piloto solo si se confirma como requisito obligatorio.

## 7. Evolución posterior al MVP local

Estas líneas no deben retrasar el primer cierre de préstamo privado y plan de reposición; se priorizan una vez aceptada la operación local o si la comisión cambia formalmente el alcance.

1. **Correcciones efectivas auditables:** definir autorización/aprobación, nueva versión o asiento correctivo, reconstrucción de posiciones/XIRR, preservación de reportes históricos y prevención de doble contabilización. Las propuestas v026 actuales no cambian los hechos originales.
2. **Análisis de inversión más profundo:** completar benchmark reproducible con instrumentos identificables, retornos brutos/netos, comisiones, distribuciones, sensibilidad y comparación contra el precio de contado cuando se confirme el requisito.
3. **Instrumentos y datos externos:** bonos/YTM, retenciones, acciones corporativas y cotizaciones obtenidas de fuentes externas con fecha, fuente y estado de validación; nunca autoetiquetar una cifra manual como observada.
4. **Identidad y operación remota:** autenticación online, recuperación de cuenta y aislamiento multiusuario solo con una arquitectura y política de seguridad explícitas. No exponer la app local actual a Internet.
5. **Distribución profesional:** licencia, versionado de releases, actualización reversible, política de soporte/retención y notas de versión. El repositorio aún no declara una licencia pública de distribución.
6. **Operación financiera asistida:** después de aceptar el MVP y reconciliar posiciones/reportes, implementar por etapas el registro textual contextual, las consultas de solo lectura y el seguimiento de reposición definidos en [CAPACIDAD_OPERATIVA_ASISTIDA.md](CAPACIDAD_OPERATIVA_ASISTIDA.md). El diseño está en backlog (#370); todavía no hay una función disponible.

## Enlaces de referencia

- [Issue coordinador #223](https://github.com/JavierGrecco/prestamos_privados/issues/223)
- [Estado actual](ESTADO_DEL_PROYECTO.md)
- [Estado de modularización](ESTADO_MODULARIZACION.md) — inventario AST de dependencias y frentes técnicos restantes
- [Roadmap de evolución técnica](ROADMAP.md)
- [Registro de cambios](REGISTRO_DE_CAMBIOS.md)
- [Instalación local](INSTALACION_LOCAL.md)
- [Diseño de carencia](DISENO_CARENCIA_INICIAL.md)


## Evidencia operativa añadida — 26/11/2026

Se incorporó `scripts/restore_drill_sintetico.py` como ejecución reproducible con datos totalmente sintéticos y servicios reales de aplicación. La prueba cubre préstamo, participación, pago, cuotas, imputaciones, ledger y auditoría; verifica backup/manifiesto, restauración en otro archivo, snapshot lógico, SHA-256, integridad y rechazo de artefacto alterado. La guía de ejecución está en [J2 — Backup verificable y restore drill](J2_BACKUP_RESTORE.md).

La automatización de PR #422 ya abre la copia restaurada con un proceso Streamlit real, lo detiene y vuelve a consultar el pago desde otro proceso y sesión Chromium. Esto no marca #374 como aceptado: falta ejecutar y registrar la guía en el entorno local de uso, inspeccionar visualmente los datos/reportes y documentar la aceptación humana.
