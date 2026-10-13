# Estado del proyecto y prioridades

**Corte:** 12 de octubre de 2026 (hora Argentina).  
**`main` actual:** [`d83f08a`](https://github.com/JavierGrecco/prestamos_privados/commit/d83f08ab99d23764d3ee5f3dd5db5853c93fc310).  
**Último commit funcional de la entrega consolidada:** [`b9e81ff`](https://github.com/JavierGrecco/prestamos_privados/commit/b9e81ff5ab810dfabe2c2ec4f6e59ca3fa7eba52).  
**Seguimiento:** [Issue #223 — MVP local P0](https://github.com/JavierGrecco/prestamos_privados/issues/223).  
**Documentos de referencia:** [Producto](PRODUCTO.md) · [Roadmap operativo](ROADMAP_MVP_LOCAL.md) · [Evaluación ejecutiva](EVALUACION_EJECUTIVA_MVP_2026-10-12.md) · [Registro de cambios](REGISTRO_DE_CAMBIOS.md).

## Resumen ejecutivo

Préstamos Privados tiene una base técnica seria e integrada: núcleo de préstamos y pagos, ledger y auditoría, superficies financieras personales, persistencia y reportes de planes de reposición, propuestas de correcciones auditables y controles importantes de atomicidad, migraciones y precisión.

Todavía **no se debe declarar el MVP local terminado ni listo para operar sin supervisión**. Los bloqueos principales son contractuales/temporales, la aceptación visual y funcional en la instalación local, la conciliación completa de posiciones/reportes, y la demostración operativa de backup/restauración y concurrencia desde la interfaz.

## Evidencia del commit actual

El CI de `main` para el commit `d83f08ab99d23764d3ee5f3dd5db5853c93fc310` terminó correctamente:

- **1.061 pruebas aprobadas en cada versión de Python 3.11, 3.12, 3.13 y 3.14.**
- CodeQL y auditoría de dependencias aprobados.
- [Matriz de pruebas](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38336979375) · [Seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38336979301).

La cifra es por cada versión de Python, no una suma de cuatro suites diferentes. CI verde valida el estado automatizado del commit, pero no prueba por sí mismo que una persona completó los recorridos en navegador ni que restauró una copia histórica.

## Evaluación y estimación

| Medida | Estimación actual | Cómo leerla |
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
| Identidad local y capacidades N1–N3 | Integrado con límites | Modelo de sesión/capacidades; el modo local no equivale a autenticación online |
| Planes de reposición v022–v025 | Integrado | Snapshots/versiones, aportes, flujos, valuaciones declaradas, XIRR condicionada e informes Markdown/JSON/CSV |
| Propuestas de corrección v026 | Integrado | Historial y comparación de propuestas inmutables; no aplican cambios efectivos al original |
| Hardening PR #258 | Integrado | Idempotencia y concurrencia Legacy, validación de entradas, rollback de operaciones anidadas, barrera de migraciones, precisión Decimal y reglas HTML |
| Correcciones auditables PR #260 | Integrado | Propuesta con autorización, motivo, hash, idempotencia e historial |
| Calendario por fechas y carencia | Base técnica, no operativa completa | La autoridad temporal existe, pero no controla aún todo el recorrido contractual/pagos/reportes |

## Bloqueos y orden de prioridad

### P0 — Decisiones financieras contractuales

- [#145 — divergencias Legacy/V3](https://github.com/JavierGrecco/prestamos_privados/issues/145): documentar y aprobar metodología de mora e imputación para escenarios sensibles. Legacy sigue vigente hasta que exista decisión y evidencia suficientes.
- [#189 — amortización por fechas y convención](https://github.com/JavierGrecco/prestamos_privados/issues/189): definir el significado contractual de TNA/TEA para períodos regulares e irregulares, reglas de calendario, fin de mes y año bisiesto. La alta real sigue admitiendo solo `MENSUAL`.
- [#186](https://github.com/JavierGrecco/prestamos_privados/issues/186) y [#192](https://github.com/JavierGrecco/prestamos_privados/issues/192): carencia. No habilitarla para operaciones reales hasta integrar contrato, cuotas, pagos parciales, adelantos, mora, ledger y reportes.

### P1 — Aceptación de los dos recorridos de producto

- **Préstamo privado:** alta, revisión del contrato, cuotas, pagos totales/parciales, adelantos permitidos, mora, distribución, auditoría e informes.
- **Autocrédito/reposición:** crear/guardar/versionar/reabrir/exportar un plan; explicar capital a reponer + referencia USD + rendimiento objetivo/costo de oportunidad; conciliar los datos declarados con posiciones e informes sin doble contabilización.
- Registrar resultados, capturas o evidencia reproducible y defectos en [#223](https://github.com/JavierGrecco/prestamos_privados/issues/223).

### P2 — Operación segura y gobierno

- Completar instalación/reinicio y backup/restauración en una ruta distinta; verificar saldos, ledger, auditoría e informes ([#156](https://github.com/JavierGrecco/prestamos_privados/issues/156), [#160](https://github.com/JavierGrecco/prestamos_privados/issues/160)).
- Ejecutar E2E de dos sesiones UI con pagos concurrentes e idempotencia ([#159](https://github.com/JavierGrecco/prestamos_privados/issues/159)).
- Ampliar las pruebas de seguridad HTML ([#158](https://github.com/JavierGrecco/prestamos_privados/issues/158)).
- Configurar protección de rama y checks requeridos de GitHub ([#157](https://github.com/JavierGrecco/prestamos_privados/issues/157)).

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

La última revisión confirmó que PR #258 y PR #260 están integrados; el trabajo de documentación #261 y #262 también se integró en `main`. Los PRs #240–#245 continúan abiertos como borradores de una secuencia anterior y han sido superados en gran parte por la consolidación del #260. No se cuentan como entregas separadas ni deben confundirse con trabajo integrado. Corresponde cerrarlos como supersedidos una vez verificado que su evidencia y decisiones quedaron conservadas en main.

Un cambio está **Integrado** solo si está en `main` y su CI pasó. Está **Aceptado** únicamente cuando además se completó la validación funcional/operativa que le corresponde.

## Documentos de referencia

- [Roadmap MVP local: fases, dependencias y criterios de salida](ROADMAP_MVP_LOCAL.md)
- [Descripción oficial y funciones del producto](PRODUCTO.md)
- [Evaluación, nota, porcentajes y comparación profesional](EVALUACION_EJECUTIVA_MVP_2026-10-12.md)
- [Arquitectura](ARCHITECTURE.md)
- [Instalación local](INSTALACION_LOCAL.md)
- [Seguridad](../SECURITY.md)
- [Índice de documentación](INDEX.md)
