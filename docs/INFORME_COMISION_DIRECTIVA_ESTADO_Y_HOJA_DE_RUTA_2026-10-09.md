# Informe para la comisión directiva: estado real, brechas y hoja de ruta

**Proyecto:** Préstamos Privados / Motor Financiero V3  
**Corte de revisión:** 10 de octubre de 2026, hora de Argentina (UTC−3)  
**Referencia de código:** `main` en `cf1a52bba8b8274d974d5eaa015189548f4fbb49`  
**Objetivo prioritario:** completar una aplicación local, utilizable desde su entorno visual, para préstamos entre personas privadas/amigos y para el caso de autocredito/reposición de capital con análisis de inversión.  
**Naturaleza de la estimación:** evaluación de ingeniería a partir del estado del repositorio, CI, documentación e incidencias abiertas. Los porcentajes y plazos que siguen son estimaciones, no mediciones automáticas ni una garantía contractual.

---

## 1. Conclusión ejecutiva

**El proyecto tiene una base técnica sólida y bastante más que un prototipo, pero todavía no está terminado para el objetivo solicitado.** Ya existe una aplicación Streamlit con operaciones de préstamo, pagos, gestión de personas, auditoría, reportes y un motor financiero separado; además, hay una superficie de análisis para reposición de capital en USD que ya compara escenarios e historial. La principal brecha dejó de ser “crear una pantalla” y pasó a ser **cerrar el circuito entre las reglas financieras, el contrato persistido, los roles, los movimientos reales y la experiencia completa de principio a fin**.

En el corte consultado:

- `main` está en el commit `cf1a52b`; el PR #237 ya se integró después de pasar los tests Python 3.11–3.14, CodeQL y auditoría de dependencias. Los workflows post-merge de `main` se comprueban por separado.
- La verificación automática cubre Python 3.11, 3.12, 3.13 y 3.14; el cambio de reporte recién integrado pasó además CodeQL y auditoría de dependencias. No se usa un recuento de tests como medida del avance funcional.
- El esquema llega a la migración v025: análisis persistido, planes/versiones de reposición, aportes de reposición, flujos/valuaciones declarados y rendimientos reportados. La exportación por plan ya incluye la proyección guardada.
- El issue coordinador [#223](https://github.com/JavierGrecco/prestamos_privados/issues/223) sigue abierto como criterio de salida del MVP; la terminación se decide por recorridos aceptados, no por cerrar tareas de forma aislada.

Esas cifras demuestran actividad y una red de regresión valiosa; no demuestran por sí solas que el producto esté listo para su uso cotidiano. No se publica un porcentaje de cobertura de código en el workflow principal, y siguen pendientes algunas pruebas de aceptación manual e integración completa de negocio.

### Dictamen para decidir

| Pregunta | Evaluación |
|---|---|
| ¿Hay un producto real funcionando en local? | **Sí, en varias rutas de operación y análisis.** |
| ¿La base técnica es buena? | **Sí: alta para una aplicación local en evolución**, por separación de capas, precisión decimal, transacciones, auditoría, documentación y CI. |
| ¿Ya están completos todos los casos de préstamos privados? | **No del todo.** Los flujos habituales están construidos; faltan cerrar reglas contractuales/temporales y algunas barreras operativas. |
| ¿El autocredito está terminado como préstamo + inversión? | **Todavía no.** Ya tiene planes/versiones, aportes de reposición, libro de inversión/valuaciones y reporte exportable de proyección versus hechos declarados; falta conectarlo a los recorridos contractuales, pagos, posiciones y aceptación manual. |
| ¿Conviene priorizar nube, identidad online o conexión a mercados? | **No para esta entrega.** Primero hay que terminar, aceptar y estabilizar la experiencia local. |
| Estimación realista hasta un MVP local completo del alcance acordado | **25–40 jornadas de ingeniería**, normalmente **5–8 semanas de trabajo a tiempo completo** o **8–12 semanas calendario** si la dedicación es parcial y hay ciclos de revisión. |

La recomendación es congelar funcionalidades no esenciales y tratar la entrega como un **MVP local controlado**, con alcance y criterios de aceptación verificables. No recomiendo declarar el producto terminado solo por la cantidad de pruebas ni activar el cut-over del Motor V3 antes de resolver las divergencias financieras ya detectadas.

---

## 2. Qué se revisó y cómo se estimó

La revisión incluyó el commit de `main`, el resultado de los checks publicados por GitHub, el árbol de código, los documentos funcionales/arquitectónicos y las incidencias abiertas de mayor impacto para el alcance local. El código está organizado en capas:

- **Dominio:** reglas de amortización, intereses, mora, devengamientos, distribución de pagos, carencia, XIRR y escenarios.
- **Aplicación:** casos de uso, consultas financieras, servicios de préstamos/pagos, seguridad de sesión y auditoría.
- **Infraestructura:** SQLite, repositorios y migraciones.
- **UI:** Streamlit, navegación por capacidades, alta y consulta de préstamos, pagos, informes y simuladores.

El porcentaje de avance es una **estimación de producto ponderada por capacidades utilizables y criterios de salida**, no un cálculo por líneas de código, commits, documentación o número de pruebas. Una función se considera cerrada cuando existe en la capa adecuada, se puede usar desde la UI, conserva los hechos económicos, pasa sus regresiones y su recorrido de usuario está validado.

---

## 3. Estado funcional por frente

Los rangos indican cuánto del **resultado esperado para este pedido** parece estar resuelto. No deben sumarse como si todas las áreas pesaran lo mismo.

| Frente | Avance estimado | Estado real | Brecha que impide marcarlo como terminado |
|---|---:|---|---|
| Núcleo de cálculo y pagos | **75–85%** | Maduro en muchos casos: amortización, pagos totales/parciales, mora, adelantos RAI/RNI, devengamientos, asignación a inversores, auditoría y reportes. | Resolver formalmente las divergencias sensibles Legacy/V3 y cerrar las reglas temporales/contractuales restantes. |
| Préstamos privados entre personas | **70–80%** | Existe alta, participación de varios inversores, ciclo de vida, registro de pagos y trazabilidad en UI. | Contratos con carencia aún no quedan integrados de extremo a extremo; convención temporal y criterio de salida financiero requieren cierre; falta completar y ejecutar aceptación integral. |
| Ejecución local e instalación | **75–85%** | Hay scripts para preparar el entorno e iniciar con ruta explícita de SQLite, guía multiplataforma, primer ADMIN, inspección de esquema y bloqueo de migraciones no autorizadas. | Probar manualmente el primer acceso y el reinicio posterior en entornos representativos; fijar dependencias; validar backup/restauración y actualizaciones sobre copias reales controladas. |
| UX y entorno visual | **65–75%** | Navegación agrupada, tema oscuro por defecto, roles/capacidades, contraste y pantallas de producto M1–M7 integrados. | Falta aceptación visual manual, responsive/anchos, vacíos y errores, y ejecutar una matriz integral con datos de prueba. |
| Autocredito / reposición + inversión | **50–60%** | Simulador USD, benchmark y backtest, planes versionados, aportes destinados a reposición, flujos y valuaciones de inversión, XIRR condicionada y reportes Markdown/JSON/CSV que separan la proyección guardada de los movimientos declarados. | Faltan aceptación manual, integración completa con el alta/pagos de préstamo, posiciones e informes personales, correcciones auditables y validación del comportamiento con casos reales controlados. El precio contado/cobertura del bien puede seguir fuera del piloto si no se aprueba como requisito. |
| Seguridad y operación para una sola máquina | **60–70%** | Cuentas locales, contraseñas protegidas, bloqueo, capacidades, auditoría, backups y control de migraciones. CI ejecuta tests, CodeQL y auditoría de dependencias. | Ampliar auditoría de todas las salidas HTML dinámicas, probar sesiones/concurrencia real de Streamlit, reforzar las pruebas de migraciones históricas y configurar protección administrativa de `main`. |
| Producto local integrado para el pedido completo | **60–65%** | Hay una aplicación local con superficies operativas y una vertical de reposición/inversión persistida y trazable. | Faltan las conexiones end-to-end entre las reglas acordadas, contrato/calendario, pagos, saldos y perspectivas de cada parte, además de aceptación manual, backup/restauración y cierre de los riesgos operativos. |

**Lectura correcta:** el producto está por encima de la mitad y aproximadamente a tres quintos del alcance local priorizado. El trabajo restante se concentra en integración, decisiones financieras que afectan importes, estabilidad y aceptación; no en rehacer desde cero la base técnica.

---

## 4. Qué está construido y merece conservarse

### 4.1 Préstamos privados

Ya existen las superficies para alta de préstamo, asignación de uno o varios inversores, cronograma de cuotas, pagos completos y parciales, mora, adelantos, consultas de deuda, detalle financiero, personas, garantías, auditoría y exportaciones. El sistema también diferencia hechos históricos, proyecciones y escenarios, y evita que la UI sea una autoridad financiera paralela.

**Esto representa una ventaja real:** no hace falta volver a empezar ni reemplazar la arquitectura. El foco debe ser completar las reglas pendientes y validar que la ruta operativa y las métricas que ve el usuario correspondan a la misma operación.

### 4.2 Autocredito y reposición de capital

En los últimos cambios se añadieron al simulador y a su capa de persistencia:

- tasas de benchmark manuales con costos e impuesto estimado;
- escenarios conservador/base/alto sobre el mismo calendario;
- importación de índices históricos total-return;
- derivación aproximada de un índice desde precio no ajustado y distribuciones por unidad;
- condición explícita para clasificar la serie como bruta o neta;
- retorno acumulado, CAGR, caída máxima, backtest histórico de capital/cuotas, XIRR y CSV con procedencia.

Se han agregado salvaguardas para no contar dos veces distribuciones, para no extrapolar fechas fuera de cobertura y para no usar una serie histórica corta o discontinua como tasa base. Esto es una base analítica útil y trazable.

Además, los PR #227, #229 y #232 incorporaron identidad y versiones inmutables del plan (v023), aportes reservados para reposición (v024) y flujos/valuaciones de inversión con XIRR condicionada (v025). El PR #237 añade la proyección original preservada al informe: Markdown muestra los supuestos y valores comparados, JSON conserva el snapshot íntegro y CSV distingue filas de supuestos/proyecciones de los movimientos declarados. Todo se mantiene como plan interno, sin convertir un rendimiento objetivo o una valuación abierta en ingreso realizado.


**Límite fundamental:** el benchmark contrafactual sigue siendo una simulación y no garantiza rendimientos. Ahora el sistema también permite registrar movimientos y valuaciones declarados por el usuario, pero no los concilia automáticamente con un broker ni comprueba las fuentes. El plan interno no crea un crédito legal contra uno mismo ni habilita por sí solo pagos contractuales; tampoco modela todavía de forma especializada bonos, rendimiento al vencimiento, splits o todas las retenciones/acciones corporativas.

### 4.3 Motor de pagos V3

Existe una implementación avanzada con persistencia, idempotencia, control de revisión, modo SOMBRA, preflight, rollback, evidencia y herramientas de canary. No se debe retirar Legacy ni cambiar la autoridad efectiva únicamente porque la suite pase: la matriz financiera detectó divergencias sensibles en mora y asignación entre interés/capital.

Para cerrar primero el producto local, la recomendación es **mantener el camino actualmente efectivo como autoridad operativa, con su modo documentado y sus controles**, mientras se resuelven las divergencias y se realiza la adopción de V3 de manera controlada. La migración/cut-over puede seguir siendo una línea paralela y posterior; no tiene que bloquear pantallas y casos de uso que puedan validarse con seguridad sobre la autoridad actual.

---

## 5. Brechas prioritarias para el alcance pedido

### P0 — Decisiones y reglas que afectan importes o contratos

1. **Definir una autoridad financiera.** Resolver las diferencias Legacy/V3 en mora y waterfall con escenarios reproducibles, importes de referencia y criterio explícito de aceptación.
2. **Cerrar las convenciones temporales.** Definir el tratamiento de TNA/TEA para períodos mensuales regulares e irregulares y para las distintas convenciones de días. El alta actual conserva la convención declarada, pero el issue correspondiente señala una inconsistencia entre esa configuración y el generador de la tabla regular.
3. **Hacer operativa la carencia permitida.** El simulador tiene tratamientos analíticos, pero las condiciones deben formar parte de una versión inmutable del contrato y quedar reflejadas en las cuotas/componentes y los pagos. No habilitar automáticamente todos los tratamientos: capitalización y cobros durante la carencia requieren reglas específicas.
4. **Separar dos conceptos de autocredito.** Un préstamo entre personas distintas es una obligación financiera real. Un plan de reposición de capital propio sirve para planificar y medir costo de oportunidad y no debe inventar un acreedor distinto ni una deuda jurídicamente exigible contra uno mismo. Los dos pueden compartir cronograma y análisis, pero deben identificarse y contabilizarse correctamente.

### P0 — Caso de uso de autocredito, de punta a punta

5. **Completar la integración del modelo de roles.** Ya existe el tipo de plan interno separado del plan de préstamo entre personas y la persistencia versionada; sigue pendiente completar el recorrido de usuario y garantizar que la posición consolidada elimine saldos internos sin ocultar el objetivo de reposición ni registrar intereses internos como ganancias externas.
6. **Conectar el plan persistido al resultado operativo completo.** Ya se puede guardar/consultar el plan con supuestos versionados, registrar aportes de reposición y flujos/valuaciones de inversión y exportar la proyección junto con los hechos declarados. Falta conectarlo con pagos, posiciones y reportes de la aplicación; los créditos reales a terceros deben convertirse en contratos solo con una secuencia explícita de revisión y aceptación.
7. **Mostrar las dos perspectivas.** Para el deudor: monto recibido, fechas, cuotas, costo total y obligación real cuando exista. Para el prestamista/inversor: capital aportado, cuotas cobradas, capital recuperado, rendimiento según flujos y saldo por recuperar. Para el autocredito propio: meta de reposición, unidad USD de referencia, benchmark/costo de oportunidad y brecha, claramente marcados como internos.
8. **Separar monedas.** Mantener diferenciados capital desembolsado en ARS, moneda contractual, unidad de referencia USD, cotización aplicable a cada pago y moneda realmente pagada. El simulador USD actual es analítico; el soporte operativo de obligaciones y pagos denominados en USD no debe darse por terminado por eso.

### P1 — Experiencia integrada y seguridad local

9. **E2E de la operación completa:** alta → confirmación → contrato/calendario → pago completo/parcial/atrasado/adelanto → lectura de deuda → posición del inversor/deudor → auditoría → exportación.
10. **Migraciones y recuperación:** pruebas desde bases históricas representativas hasta la versión actual, comparación de importes/fechas/relaciones antes y después, backup verificado y ensayo de restauración.
11. **Seguridad de UI:** inventariar las interpolaciones HTML dinámicas que siguen pendientes, cubrirlas con pruebas y revisar los puntos que usan `unsafe_allow_html`. Los cambios recientes reducen superficie, pero el issue de auditoría sigue abierto.
12. **Instalación local validada por una persona:** ejecutar comandos de la guía, primer acceso, cierre y reinicio; registrar qué plataformas se probaron realmente.
13. **Aceptación visual:** revisar tema oscuro, teclado, tamaños de pantalla, textos truncados, tablas, errores y formularios vacíos con datos reales de prueba. Dark es la preferencia por defecto y no es un defecto.

### P2 — Mejora después del MVP local

- indicador de cobertura del precio de contado del vehículo objetivo;
- modelado específico por instrumento (bonos, cupones, distribuciones, gastos, retenciones y reglas fiscales aplicables);
- nuevas fuentes automáticas de mercado, si se deciden y se autorizan;
- identidad online/multiusuario web y otras capacidades no necesarias para la entrega local.

No recomiendo incluir P2 en la primera estimación de finalización local: agregaría dependencia externa, mantenimiento de fuentes y riesgos que no son necesarios para demostrar el núcleo del producto.

---

## 6. Decisión de producto recomendada para el autocredito

Conviene tener **dos tipos de operación explícitos**, relacionados pero sin mezclar su naturaleza:

### A. Préstamo privado entre partes

Es un contrato real: deudor, uno o varios inversores, aportes que suman el capital, tasa/modalidad, calendario de pagos, política de mora, adelantos, pagos efectivos y evidencia de aceptación. El interés es costo financiero del deudor e ingreso/rendimiento del prestamista de acuerdo con los hechos y términos registrados.

### B. Plan interno de reposición de capital

Es una planificación financiera interna. Parte del capital efectivamente utilizado —por ejemplo, para comprar el vehículo— y define cuánto se busca recomponer a lo largo del tiempo. Debe permitir comparar:

- reposición nominal en ARS;
- reposición en una unidad de referencia USD;
- rendimiento objetivo/benchmark de la inversión que se dejó de mantener;
- costos/impuesto y escenarios;
- valor futuro del capital original frente a cuotas que se reinvierten;
- cobertura del objetivo, cuando exista un precio de contado registrado.

Este plan **puede usar vocabulario y cronogramas de préstamo** para que sea fácil de entender, pero debe rotular el interés como costo de oportunidad/rendimiento interno objetivo y excluir saldos internos al consolidar el patrimonio. No debe contabilizarse como ganancia efectiva antes de que exista una inversión/cobro real que lo genere.

### Regla para no crear deuda ficticia

Si el dinero lo aporta realmente la pareja, un amigo u otro inversor, se registra un crédito real entre esas partes. Si la misma persona usa fondos propios y se los “devuelve” a sí misma, se registra un plan interno. Si la operación mezcla fondos propios con dinero de otra persona, se separa el tramo interno del tramo exigible al tercero. Esto permite atender el uso de autocredito sin borrar roles financieros ni construir una relación acreedor/deudor artificial.

---

## 7. Hoja de ruta propuesta

La secuencia prioriza una versión local útil y estable. Los tiempos son rangos de ingeniería para una persona técnica con apoyo de herramientas de desarrollo, suponiendo que la comisión responda las decisiones de producto a tiempo. No incluyen nuevas funcionalidades externas ni tiempo de espera por aprobaciones.

| Fase | Duración orientativa | Entregable y criterio de salida |
|---|---:|---|
| **0. Congelar alcance y autoridad financiera** | 2–3 días | Lista firmada de casos de uso, reglas de tasa/convención de días, modo operativo Legacy/V3 para el MVP y diferencia entre crédito real y reposición propia. Cada regla sensible tiene ejemplo numérico aprobado. |
| **1. Cerrar los contratos base del préstamo** | 4–6 días | Contrato/versión inmutable; calendarios de fechas y convenciones coherentes; carencia compatible con ledger; pagos y saldos preservan invariantes; pruebas de migración aditiva sin alterar operaciones existentes. |
| **2. Integrar el plan interno persistido con la operación local** | 3–5 días restantes orientativos | La identidad, versiones, aportes y flujos/valuaciones ya existen. La salida de fase es conectar el caso interno a la navegación/posiciones/reportes, explicar el efecto sobre el patrimonio y demostrar que no genera deuda ficticia ni doble conteo. |
| **3. Integrar la UI de los dos recorridos** | 4–6 días | Préstamo privado y plan interno se completan desde el entorno visual, con resumen antes de confirmar, calendario, costos/rendimiento, datos reales frente a supuestos y mensajes explicativos. El plan interno guarda una versión auditable y se puede reabrir. |
| **4. Conectar pagos, posiciones e informes** | 3–5 días | Para crédito real: pagos, mora, adelantos, cuotas restantes, participaciones y auditoría coinciden. Para reposición interna: cobros/aportes y benchmark se muestran sin convertir el rendimiento hipotético en efectivo realizado. CSV/reportes incluyen supuestos y referencia. |
| **5. Estabilización local y controles** | 4–6 días | Matriz de migraciones históricas, backup/restore, HTML seguro, flujos de errores, E2E, primer acceso/reinicio y prueba visual. Se documenta la configuración administrativa pendiente de branch protection. |
| **6. Aceptación y paquete de entrega** | 3–5 días | Comisión/usuario ejecuta una matriz de casos con base limpia y datos ficticios, cada criterio queda marcado como aprobado o defectuoso; guía operativa, límites conocidos, versión y procedimiento de backup quedan publicadas. |

**Esfuerzo restante revisado:** aproximadamente **20–32 jornadas de ingeniería**, reservando margen para reglas financieras, integración y regresiones; unas **4–7 semanas de trabajo a tiempo completo** o **6–10 semanas calendario** con dedicación parcial, aceptación humana o decisiones demoradas. Es un rango revisable y no una promesa.

### Hitos para la comisión

- **Hito 1 — Base privada estable:** el camino habitual de préstamo/pagos queda cerrado en reglas aceptadas, con backup y regresiones.
- **Hito 2 — Autocredito utilizable:** se puede crear, reabrir y entender un plan interno desde la UI; el préstamo real a otra persona se mantiene separado; el análisis de inversión y sus supuestos quedan vinculados y trazables.
- **Hito 3 — Candidato a piloto local:** una persona externa al desarrollo instala la aplicación, crea o abre una base, opera los casos acordados, cierra la aplicación y vuelve a entrar sin perder datos; las pruebas críticas y la matriz de aceptación están verdes.
- **Hito 4 — Estabilización posterior:** decidir el canary/cut-over del Motor V3 cuando haya evidencia de equivalencia suficiente. No debe adelantarse para cumplir la fecha del MVP si siguen sin resolverse divergencias económicas.

---

## 8. Criterios de “terminado” del MVP local

El producto no se considera terminado hasta que una persona que no desarrolló el sistema pueda ejecutar estos recorridos desde la interfaz.

### Caso 1 — Préstamo real entre amigos/privados

1. Crear/verificar personas y sus roles.
2. Cargar un deudor y uno o más inversores con participaciones que sumen exactamente el capital.
3. Simular, revisar y confirmar tasa, modalidad, fechas, plazo, cuotas, costo total y las condiciones de carencia permitidas.
4. Registrar pago completo, parcial, vencido y adelanto según la política aprobada.
5. Verificar saldo, imputación, mora, participación de cada inversor y auditoría contra los cálculos esperados.
6. Cerrar/abrir la app, generar backup y comprobar restauración sobre una copia.
7. Exportar un informe que distinga lo pagado de lo proyectado.

### Caso 2 — Autocredito/reposición propia

1. Registrar el capital usado, fecha y cotización/documentación inicial.
2. Crear un plan interno de reposición con objetivo nominal y unidad de referencia, plazo, tasa objetivo/benchmark y escenarios.
3. Ver capital objetivo, cuotas programadas, costo de oportunidad y diferencia entre valor futuro del capital original y cuotas reinvertidas.
4. Importar historial solo si la fuente y su metodología están documentadas; revisar continuidad y clasificación bruto/neto.
5. Reabrir el plan y explicar cada cifra, con exportación de supuestos y procedencia.
6. Confirmar que el plan interno no se presenta como deuda legal ni como ingreso/ganancia realizada, y que no infla el patrimonio consolidado.
7. Cuando exista también un préstamo real de otra persona, registrar ese tramo como crédito real y mantener su rendimiento separado del tramo interno.

### Caso 3 — Instalación, actualización y recuperación

1. Instalar en un entorno limpio con instrucciones publicadas.
2. Inicializar una base nueva y crear el ADMIN inicial.
3. Cerrar y reiniciar el sistema conservando la misma base y usuario.
4. Intentar abrir una base con migraciones pendientes y comprobar que no se actualiza silenciosamente.
5. Generar backup verificable, migrar una copia representativa y validar integridad/datos económicos.
6. Restaurar el backup y documentar el resultado.

**Release gate:** los tres recorridos deben aprobarse sin defectos financieros críticos abiertos. Un test unitario verde no sustituye estos pasos de aceptación.

---

## 9. Qué queda fuera de la estimación y cómo evitar que crezca el alcance

Para cumplir la prioridad directiva, dejaría explícitamente fuera de esta entrega:

- despliegue web multiusuario/Internet e identidad online;
- APIs o conexión automática con proveedores de precios/cotizaciones;
- ejecución/órdenes de inversión real;
- valoración integral de cada tipo de bono, cupón, impuesto, retención, split y acción corporativa;
- migración/cut-over definitivo de V3 si no supera primero la salida financiera;
- el indicador de cobertura de precio del vehículo, salvo que la comisión lo considere requisito obligatorio del primer piloto.

Si el precio de contado del vehículo es parte imprescindible para la primera demostración, incorporar el alcance acotado de la incidencia #201 puede sumar aproximadamente **2–4 jornadas**. Un feed de mercado real o un modelo instrumentado completo no puede presupuestarse de forma responsable hasta definir fuentes, instrumentos y alcance fiscal.

---

## 10. Riesgos que conviene gestionar, no ocultar

| Riesgo | Impacto | Mitigación en el MVP |
|---|---|---|
| Diferencias financieras Legacy/V3 | Puede cambiar mora o distribución de pagos. | Mantener la autoridad actual del flujo operativo; aprobar escenarios de referencia; no hacer cut-over automático. |
| Carencia no integrada al contrato operativo | El cálculo puede existir sin corresponder al préstamo guardado. | Persistir política/condiciones versionadas y probar contrato-cuotas-pagos como una única secuencia. |
| Deudor/inversor coincidentes | Bloquea el modelo actual de reposición propia. | Introducir la modalidad interna explícita y preservar la validez del crédito entre terceros. |
| Migración de una DB con historia | Riesgo de alterar datos reales durante una actualización. | Migración aditiva, backup comprobado, fixtures históricos y restauración. |
| HTML dinámico y sesiones compartidas | Datos introducidos por usuario y estados de UI podrían afectar la experiencia/seguridad. | Completar inventario de HTML, pruebas de rutas y una aceptación local de una sola sesión; no anunciar multiusuario web. |
| Datos históricos incorrectos/incompletos | El benchmark puede generar una falsa impresión de retorno. | Exigir fuente/metodología, precio no ajustado y distribución explícita; bloquear CAGR si la serie no cubre el horizonte o tiene huecos relevantes. |
| Estimación demasiado optimista | Reglas no decididas fuerzan rediseño y retrasan la aceptación. | Congelar alcance, resolver decisiones en fase 0 y presupuestar margen de 25–40 jornadas. |

---

## 11. Decisiones que la comisión debe aprobar al inicio

Para proteger el plazo propuesto, la comisión debería aprobar por escrito:

1. **Autoridad de cálculo del primer MVP:** qué ruta operativa queda efectiva mientras se resuelve la equivalencia Legacy/V3.
2. **Política de cuotas y carencia:** modalidades permitidas, cálculo de interés por período, convención de días y reglas del primer período irregular.
3. **Naturaleza del autocredito:** plan interno de reposición separado del préstamo exigible a terceros; cómo se refleja en vistas individuales y consolidadas.
4. **Alcance de moneda:** para esta entrega, mantener contratos y pagos operativos en las modalidades ya aceptadas; USD como referencia analítica donde aún no exista una regla contractual aprobada. No anunciar el simulador como soporte completo de deuda/pago real en USD.
5. **Criterios de aceptación y responsable:** qué persona validará los dos casos financieros y quién ejecutará la prueba de instalación/restauración.
6. **Límites del MVP:** qué capacidades P2 se aceptan explícitamente para después.

---

## 12. Evaluación final de calidad y potencial

### Calidad actual

Mi valoración cualitativa, no una auditoría externa certificada, es:

- **Base de ingeniería: alta (aprox. 8/10).** Separación de responsabilidades, precisión decimal, transacciones, auditoría, documentación y regresión automatizada están por encima de un prototipo básico.
- **Producto local integrado respecto del pedido: media (aprox. 6/10).** La base es sustancial y el plan interno ahora se guarda y reporta, pero el producto aún necesita cerrar las rutas operativas y la aceptación de punta a punta.
- **Autocredito como flujo integrado: medio (aprox. 5–6/10).** Ya existe persistencia/versionado, aportes, movimientos, valuaciones, XIRR condicional y reporte que contrasta proyección con hechos declarados; todavía no hay una experiencia unificada con pagos, posiciones, consolidación y aceptación completa.
- **Potencial del producto final:** alto si se completa la integración y la aceptación. No hace falta reescribirlo; sí resolver cuidadosamente las reglas financieras y no llamar “terminado” a lo que actualmente solo es simulación.

### Estimación recomendada

**Presupuestar alrededor de 4–7 semanas de trabajo técnico concentrado a partir de este corte, con reserva de 6–10 semanas calendario si la dedicación es parcial o las reglas requieren revisión. La entrega prioritaria debe terminar con rutas probadas por personas, no solo con una lista de funcionalidades integradas.

La recomendación directiva es **terminar primero la experiencia local de préstamos reales y reposición/autocredito, estabilizar la operación y validar el producto; después profundizar el benchmark o ampliar a multiusuario**. Esa secuencia aprovecha lo ya invertido, reduce el riesgo y permite poner una versión útil en manos de usuarios sin fingir que la parte todavía no integrada ya está resuelta.

---

## Referencias dentro del repositorio

- [Estado actual del proyecto](ESTADO_DEL_PROYECTO.md)
- [Producto y superficies funcionales](PRODUCTO.md)
- [Hoja de ruta existente](ROADMAP.md)
- [Instalación local](INSTALACION_LOCAL.md)
- [Diseño de autocredito/reposición](DISENO_AUTOPRESTAMO_COBERTURA_CAMBIARIA.md)
- [Diseño financiero de carencia](DISENO_CARENCIA_INICIAL.md)
- [Issue #194: roles coincidentes y autocredito](https://github.com/JavierGrecco/prestamos_privados/issues/194)
- [Issue #192: contrato persistente de carencia](https://github.com/JavierGrecco/prestamos_privados/issues/192)
- [Issue #189: convenciones temporales](https://github.com/JavierGrecco/prestamos_privados/issues/189)
- [Issue #202: reposición de capital y rendimiento objetivo](https://github.com/JavierGrecco/prestamos_privados/issues/202)
- [Issue #204: benchmark de inversión](https://github.com/JavierGrecco/prestamos_privados/issues/204)
- [Issue #145: divergencias Legacy/V3](https://github.com/JavierGrecco/prestamos_privados/issues/145)
- [Issue #179: aceptación integral](https://github.com/JavierGrecco/prestamos_privados/issues/179)
