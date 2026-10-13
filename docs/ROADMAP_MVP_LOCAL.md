# Hoja de ruta de implementación — MVP local

**Corte de estado:** 12 de octubre de 2026 (hora Argentina)  
**Rama/commit de referencia:** `main` — `d83f08ab99d23764d3ee5f3dd5db5853c93fc310`  
**Último commit funcional integrado:** `b9e81ff5ab810dfabe2c2ec4f6e59ca3fa7eba52`  
**Seguimiento coordinador:** [Issue #223 — MVP local P0](https://github.com/JavierGrecco/prestamos_privados/issues/223)  
**Evaluación ejecutiva, calificación y estimación:** [EVALUACION_EJECUTIVA_MVP_2026-10-12.md](EVALUACION_EJECUTIVA_MVP_2026-10-12.md) · **Estado detallado por área:** [Estado del proyecto](ESTADO_DEL_PROYECTO.md) · **Descripción del producto:** [PRODUCTO.md](PRODUCTO.md) · **Historial:** [Registro de cambios](REGISTRO_DE_CAMBIOS.md)

> **Este es el documento operativo principal para decidir el orden del trabajo y comprobar cuándo una fase está terminada.** El issue #223 debe reflejar su resumen y enlazar la evidencia. `ROADMAP.md` conserva la historia de los programas técnicos anteriores; no se debe usar como un segundo tablero del MVP.

## 1. Estado real a la fecha

La base funcional está integrada en `main`; el trabajo pendiente ya no se mide por cantidad de pantallas o clases, sino por recorridos completos, reglas financieras acordadas y aceptación de operación local.

La consolidación del [PR #258](https://github.com/JavierGrecco/prestamos_privados/pull/258) está en la historia de `main`. Las correcciones auditables de planes internos quedaron integradas por el [PR #260](https://github.com/JavierGrecco/prestamos_privados/pull/260), en el commit de referencia indicado arriba.

**CI del `main` de referencia (`d83f08a`):**
- **1.061 pruebas aprobadas en cada una de Python 3.11, 3.12, 3.13 y 3.14.**
- CodeQL y auditoría de dependencias aprobados.
- [Matriz de pruebas](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38336979375) · [Controles de seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38336979301)

La calificación estimada del proyecto en desarrollo es **7,0/10**; el avance funcional se estima en **65–70%** y la preparación operativa en **55–60%**. Restan **21–34 jornadas de ingeniería** según el alcance y la aceptación que se exige. Los criterios y las limitaciones de esas cifras están en la evaluación ejecutiva.

Eso confirma la suite automatizada del commit señalado. **No equivale** a aceptación visual manual, prueba de instalación limpia ni simulacro de restauración de una base histórica.

### Resumen por frente

| Frente | Estado verificable | Lo que falta para cerrarlo |
|---|---|---|
| Núcleo financiero y seguridad de persistencia | **Integrado; CI verde** | Mantener regresiones y aceptar los recorridos de producto |
| Préstamo real y calendario | **Parcial / bloqueado por decisión contractual** | La ruta operativa de alta solo admite `MENSUAL`; incorporar la autoridad temporal por fechas sin recalcular préstamos históricos |
| Carencia inicial | **Base técnica integrada; no operativa de punta a punta** | Acordar contrato y devengamiento; conectar snapshot, cronograma, pagos, mora, ledger e informes |
| Autocrédito/reposición | **Persistencia y reportes de plan integrados** | Aceptar el recorrido manual; conectar posición e informes sin doble contabilización |
| Correcciones auditables v026 | **Propuestas integradas** | Las propuestas no aplican cambios a los hechos; definir y probar un proceso de corrección efectiva en fase separada |
| Interfaz y navegación | **Implementadas; aceptación manual pendiente** | Probar los dos recorridos con instalación local y registrar resultados |
| Backup, actualización y recuperación | **Controles implementados; drill completo pendiente** | Restaurar una copia en otra ruta y verificar saldos, ledger, auditoría y reportes |
| Concurrencia de sesiones Streamlit | **Hardening y pruebas técnicas integrados** | Aceptación E2E con sesiones reales y pagos concurrentes |
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

**Estimación restante de planificación: 21–34 jornadas de ingeniería.** Es una estimación revisada a partir de las fases que siguen abiertas; tiene confianza media-baja hasta resolver las decisiones temporales y realizar la aceptación manual.

Como referencia, equivale a **4–7 semanas de dedicación completa** o **6–10 semanas calendario** con dedicación parcial, revisión humana y tiempos de decisión. Si incluir la comparación/cobertura del precio contado del vehículo es obligatorio en el primer piloto, sumar **2–4 jornadas**.

La evaluación ejecutiva publica un rango estimado de **65–70% de avance funcional** y **55–60% de preparación operativa**. El 60–65% anotado en #223 el 10 de octubre es una línea base histórica y no debe seguir presentándose como cifra actual. Los rangos actuales son estimaciones técnicas; la fase solo se cierra con evidencia de los criterios de aceptación, no por cantidad de PRs o pruebas.

| Fase | Esfuerzo restante | Estado | Referencias |
|---|---:|---|---|
| 0. Decisiones financieras y alcance | 2–3 jornadas | **En curso / bloqueante** | [#145](https://github.com/JavierGrecco/prestamos_privados/issues/145), [#189](https://github.com/JavierGrecco/prestamos_privados/issues/189), [#186](https://github.com/JavierGrecco/prestamos_privados/issues/186) |
| 1. Contrato y calendario del préstamo | 4–6 jornadas | **Pendiente de fase 0** | [#189](https://github.com/JavierGrecco/prestamos_privados/issues/189), [#192](https://github.com/JavierGrecco/prestamos_privados/issues/192) |
| 2. Autocrédito y reposición propios | 2–4 jornadas | **Integrado parcialmente; aceptación/conexión pendiente** | [#194](https://github.com/JavierGrecco/prestamos_privados/issues/194), [#202](https://github.com/JavierGrecco/prestamos_privados/issues/202), [#204](https://github.com/JavierGrecco/prestamos_privados/issues/204) |
| 3. Dos recorridos visuales completos | 3–5 jornadas | **Pendiente de aceptación manual** | [#179](https://github.com/JavierGrecco/prestamos_privados/issues/179), [#223](https://github.com/JavierGrecco/prestamos_privados/issues/223) |
| 4. Pagos, posiciones e informes integrados | 3–5 jornadas | **Parcial; reconciliación pendiente** | [#223](https://github.com/JavierGrecco/prestamos_privados/issues/223), [#201](https://github.com/JavierGrecco/prestamos_privados/issues/201), [#206](https://github.com/JavierGrecco/prestamos_privados/issues/206) |
| 5. Operación local, seguridad y recuperación | 4–6 jornadas | **Parcial; faltan drills y E2E** | [#156](https://github.com/JavierGrecco/prestamos_privados/issues/156), [#157](https://github.com/JavierGrecco/prestamos_privados/issues/157), [#158](https://github.com/JavierGrecco/prestamos_privados/issues/158), [#159](https://github.com/JavierGrecco/prestamos_privados/issues/159), [#160](https://github.com/JavierGrecco/prestamos_privados/issues/160) |
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
- Prueba de dos sesiones/hilos sobre el mismo préstamo: idempotencia, bloqueo, revisión obsoleta y ausencia de duplicación.
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
- Los issues técnicos (#145, #156–#160, #179, #186, #189, #192, #194, #201, #202, #204, #206) guardan detalle por tema.
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

## Enlaces de referencia

- [Issue coordinador #223](https://github.com/JavierGrecco/prestamos_privados/issues/223)
- [Estado actual](ESTADO_DEL_PROYECTO.md)
- [Roadmap de evolución técnica](ROADMAP.md)
- [Registro de cambios](REGISTRO_DE_CAMBIOS.md)
- [Instalación local](INSTALACION_LOCAL.md)
- [Diseño de carencia](DISENO_CARENCIA_INICIAL.md)
