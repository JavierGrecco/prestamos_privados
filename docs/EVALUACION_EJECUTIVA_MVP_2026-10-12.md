# Evaluación ejecutiva de Préstamos Privados

**Fecha de corte:** 12 de octubre de 2026, hora Argentina  
**Rama evaluada:** `main`  
**Base funcional de referencia:** `b9e81ff5ab810dfabe2c2ec4f6e59ca3fa7eba52` (PR #258 y #260); las revisiones posteriores de documentación no cambian cálculos.  
**Último commit de código funcional citado en la hoja de ruta:** `b9e81ff5ab810dfabe2c2ec4f6e59ca3fa7eba52`  
**Roadmap operativo:** [ROADMAP_MVP_LOCAL.md](ROADMAP_MVP_LOCAL.md)  
**Seguimiento coordinador:** [Issue #223 — MVP local P0](https://github.com/JavierGrecco/prestamos_privados/issues/223)

> Esta evaluación separa código integrado, funcionalidad conectada y aceptación para uso real. Los puntajes y porcentajes son una estimación técnica razonada, no una métrica automática ni una certificación externa.

## 1. Conclusión ejecutiva

Préstamos Privados tiene una base técnica sólida para una aplicación local especializada en préstamos entre personas y análisis de autocrédito/reposición. El valor ya construido incluye gestión de préstamos, calendario mensual Legacy, registro de pagos, mora, adelantos, ledger y auditoría; un Motor de Pagos V3 preparado para adopción controlada; planes propios de inversión/reposición con versiones, flujos, valuaciones, XIRR y exportación; y un registro inmutable para proponer correcciones auditables.

La diferencia con un producto terminado está en los cierres de punta a punta: reglas contractuales y temporales aprobadas, conciliación de posiciones/reportes, aceptación visual y manual, recuperación operativa verificada y decisión respaldada por evidencia para cualquier transición de Legacy a V3. El MVP **no se considera terminado ni listo para uso financiero real sin supervisión** hasta cerrar esas puertas.

## 2. Evidencia del repositorio

La base funcional de referencia incluye PR #258 (hardening financiero/temporal, commit `b0d96de`) y PR #260 (propuestas de corrección auditables, commit `b9e81ff`). PR #261, #262 y #264 alinearon la documentación de producto, el roadmap y la aceptación pendiente sin cambiar fórmulas financieras.

La matriz CI de `main` posterior al merge del PR #264 terminó en verde:
- **1.061 pruebas aprobadas en cada una de Python 3.11, 3.12, 3.13 y 3.14**.
- CodeQL y auditoría de dependencias aprobados.
- Evidencia: [tests tras el merge](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38338273679) · [seguridad tras el merge](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38338273668).

Las cuatro ejecuciones de Python son matrices de la misma suite en distintos intérpretes; no deben sumarse como si fueran 4.244 pruebas distintas. El resultado muestra buena disciplina automatizada en el `main` actual. La última matriz confirma que los cambios documentales no introdujeron regresiones. Aun así, no reemplaza recorridos reales en la interfaz, verificación de backups/restauración ni aprobación de decisiones económicas.

## 3. Calificación general

| Dimensión | Nota | Justificación |
|---|---:|---|
| Calidad técnica del código integrado | **8,0/10** | Separación por capas, SQLite controlado, trazabilidad, pruebas extensas, CI multi-Python y controles de seguridad automatizados. |
| Completitud funcional del MVP | **6,5/10** | Muchas capacidades están integradas, pero todavía no están aceptados ambos recorridos completos y algunas funciones siguen siendo propuestas/análisis, no cambios financieros efectivos. |
| Preparación para uso con dinero real | **5,5/10** | No debe declararse producción hasta cerrar reglas de calendario/contrato, conciliación, instalación/restauración manual, concurrencia en UI y aceptación funcional. |
| Potencial de diferenciación | **8,5/10** | Enfoque local/familiar, roles de persona combinables y autocrédito que evalúa reposición de capital, poder adquisitivo en USD y rendimiento alternativo. |
| **Nota global como proyecto en desarrollo** | **7,0/10** | Buena base de ingeniería; aún falta convertirla en un producto aceptado, repetible y probado de punta a punta. |

Estas notas son juicio técnico con el alcance descrito. No implican auditoría financiera independiente, certificación de seguridad ni verificación regulatoria.

## 4. Avance estimado por área

Porcentaje estimado respecto del alcance funcional previsto; no es porcentaje de líneas de código ni suma de tests.

| Área | Avance estimado | Lo que falta para cerrarla |
|---|---:|---|
| Núcleo de préstamos, cuotas y pagos | **75–80%** | Aceptar recorridos contractuales completos y verificar cuotas, pagos, mora, adelantos, saldos e informes con ejemplos aprobados. |
| Ledger, auditoría e integridad de datos | **80–85%** | Expandir pruebas operativas de recuperación y concurrencia real desde la UI; resolver aceptación de recuperación. |
| Motor V3 y adopción controlada | **70–75%** | Resolver divergencias financieras, aprobar criterio de salida y hacer canary/cut-over solo con evidencia autorizada. Legacy sigue como autoridad efectiva. |
| Autocrédito/reposición e inversión ARS/USD | **65–70%** | Aceptar el recorrido guardado/reabierto/exportado; conectar y conciliar posiciones/reportes; terminar comparación con inversión alternativa y precio de contado si es parte del primer piloto. |
| Calendario contractual y carencia real | **35–45%** | Unificar la autoridad temporal de simulador, alta, pagos e informes; integrar contrato y calendario antes de habilitar carencia en operaciones reales. |
| UI/UX y navegación | **70–75%** | Aceptación visual/manual y comprobar que las tareas principales se completan sin SQL ni scripts auxiliares. |
| Instalación, recuperación y gobierno de cambios | **60–70%** | Instalación y reinicio manual, backup/restauración en otra ruta, concurrencia E2E, checks requeridos y protección formal de `main`. |

**Estimación global de avance funcional: 65–70%.**  
**Estimación de preparación operativa con dinero real: 55–60%.**

Los rangos reflejan la aceptación pendiente, no una falta general de código. Para que estos porcentajes se conviertan en métricas verificables, cada fase debe cerrarse con evidencia de aceptación definida en el [roadmap operativo](ROADMAP_MVP_LOCAL.md).

## 5. Estimación para terminar el MVP local

La estimación de planificación vigente es de **21–34 jornadas de ingeniería**, aproximadamente **4–7 semanas con dedicación completa** o **6–10 semanas calendario con dedicación parcial**, decisiones y revisión. Si la comparación/cobertura contra el precio de contado del vehículo debe estar incluida en el primer piloto, sumar **2–4 jornadas**.

| Fase | Esfuerzo pendiente | Bloqueo principal |
|---|---:|---|
| 0. Decisiones financieras y alcance | 2–3 jornadas | Casos aprobados para tasas, fechas, mora, waterfall y carencia; decisión formal de Legacy/V3. |
| 1. Contrato y calendario | 4–6 jornadas | Una autoridad temporal y misma tabla entre simulación y contrato guardado. |
| 2. Autocrédito/reposición | 2–4 jornadas | Aceptación del plan, supuestos/proyecciones separados de flujos/valuaciones y conexión a posiciones/reportes. |
| 3. Recorridos completos de UI | 3–5 jornadas | Aceptación de préstamo privado y plan propio desde la interfaz. |
| 4. Pagos, posiciones e informes | 3–5 jornadas | Reconciliar saldos, mora, adelantos, inversiones, valuaciones y reportes en una fecha de corte común. |
| 5. Operación local segura | 4–6 jornadas | Instalación, recuperación, concurrencia, seguridad y protecciones de rama. |
| 6. Aceptación y paquete de entrega | 3–5 jornadas | Pruebas manuales por otra persona, evidencias y resolución de defectos críticos. |

La confianza de la estimación es **media-baja** hasta resolver el calendario contractual y registrar evidencia de aceptación manual. Es planificación, no promesa de fecha.

## 6. Comparación con productos profesionales

La comparación no es uno a uno: Nortridge, LoanPro y Mambu atienden operaciones de crédito de escala y despliegue distintos. Sus capacidades publicadas sirven como referencia de madurez, no como prueba independiente de su funcionamiento.

| Referencia pública | Capacidades que declaran | Qué lecciones aplican a este proyecto |
|---|---|---|
| [Nortridge — gestión de préstamos](https://nortridge.com/loan-management-software/) | Ciclo de vida configurable, administración de saldos/intereses/comisiones, pagos, cascadas de imputación, cobranzas, reportes, workflows e integraciones API. | Mantener reglas financieras configurables pero explícitas, automatizar procesos repetibles y ofrecer vistas operativas útiles, no solo cálculo. |
| [LoanPro — servicing](https://www.loanpro.io/platform/servicing-suite) y [documentación de servicing/cobranzas](https://help.loanpro.io/servicing-and-collections) | Plataforma de servicing, automatización, autoservicio de prestatarios, recálculo/recast, ledger de eventos, reportes y trazabilidad. | Robustecer eventos, idempotencia, revisión de estado, operaciones repetibles y evidencia de por qué cambió cada saldo. |
| [Mambu — capacidades de core](https://mambu.com/en/core-capabilities) | Gestión de préstamos, contratos/estados de cuenta, garantías, aprobaciones, servicing, cobranzas, contabilidad/subledger y trazabilidad transaccional. | Tratar la contabilidad, los contratos, el calendario y la conciliación como un mismo sistema coherente. |

El proyecto **todavía no iguala una plataforma de servicing empresarial en integraciones, workflows de operación, canales de autoservicio, gobierno y escala**. Tampoco necesita replicar todo eso para su objetivo local entre personas. Debería tomar las prácticas que afectan la confianza financiera y postergar las que pertenecen a una operación empresarial más grande.

Para calidad del proceso de desarrollo, el [NIST Secure Software Development Framework (SSDF)](https://csrc.nist.gov/pubs/sp/800/218/final) aporta una referencia útil para organizar protección del software, construcción segura y respuesta a vulnerabilidades. El CI actual es un buen inicio, pero también hay que formalizar revisión obligatoria, releases, gestión de fallas y recuperación.

## 7. Cómo destacar entre herramientas similares

El diferencial no debería ser simplemente “tener más pantallas” ni “usar IA”. El proyecto puede destacar por hacer muy transparente una decisión financiera compleja que las herramientas genéricas no modelan como objetivo central.

### Diferenciales que conviene convertir en producto

1. **Autocrédito con objetivo económico completo.** Medir reposición de capital + conservación del poder adquisitivo en USD + rendimiento objetivo/costo de oportunidad. No limitarse a recuperar el nominal, ni presentar rendimientos futuros como garantizados.
2. **Cada cifra explicable.** Mostrar si un valor es un dato real, una valuación declarada, un supuesto, un benchmark o una proyección; identificar fuente, fecha, cotización, regla y versión de cálculo.
3. **Contrato y simulación idénticos.** Lo que se muestra antes de confirmar debe coincidir con lo guardado y con lo que usan pagos e informes.
4. **Local-first confiable.** Que la persona conserve sus datos, pueda hacer backups verificables y restaurar una copia sin asistencia técnica.
5. **Trazabilidad entendible.** Poder responder “por qué cambió mi saldo”, “cómo se imputó este pago”, “qué versión de política se aplicó” y “qué evidencia respalda esta proyección”.
6. **Lenguaje argentino y humano.** ARS/USD, fechas, ejemplos de cuotas, términos cotidianos y vistas diferenciadas para quien presta, quien recibe y quien administra.

## 8. Plan priorizado para llegar a estándar profesional

### P0 — Cerrar reglas económicas y calendario
Resolver los issues [#145](https://github.com/JavierGrecco/prestamos_privados/issues/145), [#189](https://github.com/JavierGrecco/prestamos_privados/issues/189) y [#186](https://github.com/JavierGrecco/prestamos_privados/issues/186). Acordar ejemplos numéricos de referencia y asegurar que la simulación, el alta, los pagos y los informes usan la misma autoridad temporal. La convención `MENSUAL` sigue siendo la única admitida por el alta contractual hasta terminar esa integración. No habilitar carencia real antes del E2E completo.

### P1 — Aceptar los dos recorridos desde la UI
Completar manualmente (y registrar capturas/datos de prueba) un préstamo privado real: alta, cronograma, pago completo/parcial, adelanto cuando corresponda, mora, distribución, ledger, consulta e informe. Luego crear, guardar, cerrar/reabrir y exportar un plan de reposición con sus flujos/valuaciones claramente separados de la proyección.

### P2 — Reconciliación y control de operación
Conciliar saldo de préstamo, pagos, imputaciones, ledger, posición del inversor y reportes en la misma fecha de corte. Probar reinicio, backup verificado, restauración en otra ruta y dos sesiones de UI operando de forma concurrente.

### P3 — Gobernanza y liberaciones
Resolver [#157 — protección de main](https://github.com/JavierGrecco/prestamos_privados/issues/157): revisión obligatoria, checks requeridos y prohibición de integrar cuando falle CI. Definir versión de release, changelog, procedimiento de actualización/rollback y evidencias archivadas.

### P4 — Diferenciación por análisis transparente
Una vez aceptado el recorrido básico, completar la comparación de reposición con precio de contado, escenarios de cotización y rendimiento objetivo, con fuentes fechadas, sensibilidad y separación estricta de datos observados, supuestos y proyecciones. Integraciones con brokers y modelos más amplios de valores quedan fuera del primer cierre local si no son imprescindibles para el piloto.

## 9. Puertas de salida: qué significa “terminado”

El MVP se puede marcar terminado cuando:

- las reglas financieras del primer alcance estén aprobadas con ejemplos numéricos reproducibles;
- el préstamo y el plan de reposición puedan completarse de principio a fin desde la interfaz, sin SQL/manualidades;
- pagos, saldos, waterfall, mora, ledger y auditoría concilien;
- se conserve la distinción entre capital, interés, mora, flujo de inversión, valuación, rendimiento realizado y proyección;
- instalación limpia, reinicio, backup y restauración estén demostrados;
- CI, CodeQL y auditoría pasen en el commit de entrega;
- una persona distinta de quien implementó el código complete ambos recorridos y registre su aceptación;
- no queden defectos financieros críticos abiertos.

## 10. Límites explícitos al corte

- Legacy sigue siendo el motor efectivo; no hacer cut-over de V3 solo por calendario o porque hay más pruebas.
- No recalcular automáticamente préstamos históricos por adoptar un calendario nuevo.
- Las propuestas de corrección v026 son inmutables y auditables, pero no cambian automáticamente originales, saldos, XIRR ni informes.
- La carencia no debe habilitarse en préstamos reales hasta cerrar contrato, calendario, pagos parciales/adelantos, mora, ledger y reportes.
- La CI verde no equivale a aceptación visual ni a una prueba de restauración realizada.

## Fuentes de esta evaluación

- Estado y alcance integrados: [ESTADO_DEL_PROYECTO.md](ESTADO_DEL_PROYECTO.md).
- Plan de trabajo, dependencias y criterios de salida: [ROADMAP_MVP_LOCAL.md](ROADMAP_MVP_LOCAL.md).
- Seguimiento coordinador: [issue #223](https://github.com/JavierGrecco/prestamos_privados/issues/223).
- Evidencia CI: [tests](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38336979375) y [seguridad](https://github.com/JavierGrecco/prestamos_privados/actions/runs/38336979301).
- Referencias de producto: Nortridge, LoanPro y Mambu, enlazadas en la comparación; cifras y capacidades son las que declaran sus propias páginas.
- Referencia de desarrollo seguro: [NIST SSDF SP 800-218](https://csrc.nist.gov/pubs/sp/800/218/final).
