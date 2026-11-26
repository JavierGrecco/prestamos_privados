# Producto y alcance

**Corte de contenido funcional:** 12 de octubre de 2026 (hora Argentina); esta es la última revisión integral documentada de las superficies y recorridos del producto. La actualización técnica/documental más reciente es del 26 de noviembre de 2026 y no equivale a una nueva aceptación manual.

**Referencia técnica vigente:** `main` en [`0bae21f`](https://github.com/JavierGrecco/prestamos_privados/commit/0bae21fd44918d8d3c2140311406755bbaba8954).
**Estado:** el núcleo y las superficies descritas abajo están integrados en `main`; el MVP local todavía requiere aceptación funcional manual y cierre de decisiones financieras. La validación técnica más reciente no reemplaza esa aceptación.  
**Estado verificable:** [ESTADO_DEL_PROYECTO.md](ESTADO_DEL_PROYECTO.md) · **Roadmap operativo:** [ROADMAP_MVP_LOCAL.md](ROADMAP_MVP_LOCAL.md) · **Evaluación histórica:** [EVALUACION_EJECUTIVA_MVP_2026-10-12.md](EVALUACION_EJECUTIVA_MVP_2026-10-12.md).

## 1. Qué problema resuelve

**Préstamos Privados** es una aplicación local, en español y orientada a Argentina, para administrar préstamos entre personas y analizar la reposición de capital de un plan propio. Su propósito es ayudar a prestar, recibir, invertir y decidir con cifras explicables y trazables, sin exigir que el usuario conozca contabilidad o la implementación del motor.

El producto une dos recorridos relacionados, pero distintos:

1. **Préstamo privado:** registrar el acuerdo, calcular cuotas, registrar pagos y explicar cómo cambia cada saldo.
2. **Autocrédito/reposición:** planificar cómo reponer capital, preservar su poder adquisitivo de referencia en USD y añadir un rendimiento objetivo/costo de oportunidad, distinguiendo los hechos reales de las proyecciones.

La aplicación es local-first: usa Python, Streamlit y SQLite. No es actualmente una plataforma SaaS, un banco, un broker ni un sistema de identidad online.

## 2. Usuarios y roles

Una persona puede participar en distintas capacidades y en más de un rol financiero: deudor, inversor, garante u operador/administrador según las relaciones permitidas. El rol describe cómo participa en una operación; no sustituye autenticación ni autorización.

- **Deudor:** consulta las condiciones, cuotas, pagos y deuda conocida.
- **Inversor/prestamista:** consulta aportes, participaciones, cobros y rendimiento respaldado por registros.
- **Garante:** queda vinculado a una garantía concreta; ese vínculo no genera deuda ni cambia pagos por sí solo.
- **Operador/administrador local:** administra datos y utiliza las funciones permitidas por las capacidades configuradas.
- **Persona que planifica su propio financiamiento:** analiza un plan interno de reposición y alternativas de inversión. Un plan de análisis no constituye automáticamente un préstamo legal contra sí misma ni un cobro exigible.

**Límite de identidad:** el modo local actual no debe describirse como autenticación multiusuario real ni exponerse a Internet. N1–N3 organizan identidad de sesión, capacidades y roles; un proveedor online, recuperación por email y operación remota pertenecen a una etapa posterior.

## 3. Funciones del producto

| Superficie | Para qué sirve | Estado real |
|---|---|---|
| **Mi espacio** | Resumen personal, próximos movimientos y actividad | Integrado; aceptación visual local pendiente |
| **Préstamos** | Alta y ciclo de vida de préstamos con un deudor y uno o varios inversores | Integrado; el alta contractual operativa admite calendario mensual |
| **Pagos** | Vista previa y registro de pagos con trazabilidad | Integrado; Legacy es la autoridad efectiva hasta resolver divergencias con V3 |
| **Detalle financiero** | Amortización, capital, intereses, mora, devengamientos y adelantos RAI/RNI | Integrado; los recorridos completos requieren aceptación con casos de referencia |
| **Posición** | Resumen de capital conocido por la aplicación | Integrado; no equivale al patrimonio total de la persona |
| **Planificar y Escenarios** | Proyección de flujos conocidos bajo supuestos explícitos | Integrado; las proyecciones no modifican el contrato |
| **Rendimiento y Comparar** | Métricas disponibles y comparación de operaciones registradas | Integrado; XIRR solo cuando hay flujos suficientes y una solución defendible |
| **Planes de reposición** | Guardar/versionar planes, registrar aportes, flujos y valuaciones declarados | Persistencia y descargas integradas; aceptación y conciliación con posiciones/reportes pendientes |
| **Correcciones auditables** | Guardar y comparar propuestas de corrección con motivo y trazabilidad | Propuestas v026 integradas; no aplican automáticamente cambios al registro original |
| **Personas y garantías** | Administrar participantes, roles y garantías vinculadas a préstamos | Integrado, con límites del modo de identidad local |
| **Finanzas personales** | Evaluar una cuota con margen libre declarado; evolucionar hacia presupuesto y registro completo opcional | Primera modalidad directa integrada en Mi espacio; resto de F1 pendiente |
| **Auditoría y operación** | Consultar evidencia, integridad, backups y preparación del motor | Controles integrados; restauración histórica y aceptación local pendientes |

## 4. Objetivo económico del autocrédito/reposición

El objetivo no es recuperar solamente el capital nominal. El análisis debe mostrar por separado:

1. **Capital que se necesita reponer.**
2. **Conservación del poder adquisitivo**, usando la referencia USD y cotizaciones fechadas y con origen identificado.
3. **Rendimiento objetivo o costo de oportunidad**, comparando contra una alternativa explícita y sus supuestos, gastos y posibles distribuciones.

El resultado debe diferenciar dinero efectivamente cobrado/aportado, costo externo registrado, valuación declarada a una fecha y proyección. El rendimiento objetivo no es una ganancia garantizada ni una rentabilidad realizada. Una cotización o valuación ingresada manualmente no se convierte por eso en dato observado o validado externamente.

## 5. Reglas de confianza financiera

- **Contrato y cálculo coherentes:** lo que se confirma en la interfaz debe coincidir con las condiciones persistidas, el cronograma y lo que consumen pagos e informes.
- **Sin reinterpretar historia:** una regla nueva no recalcula automáticamente préstamos existentes.
- **Importes exactos:** dinero representado mediante `Decimal`, almacenado como texto decimal cuando corresponde, con redondeo explícito.
- **Una operación, una unidad atómica:** si falla una etapa financiera, debe revertirse la operación completa.
- **Imputación explicable:** la política aplicada, las fechas relevantes y las asignaciones deben quedar trazables.
- **Hecho, valuación, proyección separados:** ninguna pantalla debe presentar hipótesis como un movimiento realizado.
- **Corrección auditable:** no sobrescribir silenciosamente movimientos históricos; una propuesta no se considera efectiva hasta que exista un flujo de aprobación/aplicación definido.
- **Legacy/V3 controlado:** Legacy sigue como autoridad operativa hasta que las divergencias económicas se acepten y se autorice el canary/cut-over con evidencia.

## 6. Alcance y restricciones vigentes

El núcleo mensual de préstamos y pagos está desarrollado, pero **no se considera terminado el MVP local**. Para la entrega deben aceptarse ambos recorridos desde la interfaz, reconciliar saldos, ledger y reportes, y demostrar instalación, backup y restauración.

La autoridad por fechas y varias convenciones de días existen como base técnica y de simulación. El alta real queda restringida a `MENSUAL` mientras alta, pagos e informes no consuman la misma autoridad temporal. La etiqueta visible de la variante 30/360 especifica actualmente **30E/360 ISDA (ajuste de fin de mes)** y advierte la excepción del vencimiento final en febrero. Este rótulo describe el cálculo existente; cambiar el texto no cambia resultados.

La carencia inicial tiene simulación, convenciones y snapshots contractuales como base. **No está habilitada para operaciones reales de punta a punta** hasta acordar la regla contractual y probar calendario, cuotas, pagos parciales, adelantos, mora, ledger y reportes sin doble contar ni capitalizar accidentalmente el interés diferido.

Las propuestas de corrección v026 son inmutables y trazables. No cambian por sí solas el original, los saldos, XIRR, posiciones o informes. La aplicación efectiva de correcciones necesita una política explícita y pruebas de reconstrucción.

## 7. Qué queda fuera del primer MVP local

Salvo decisión expresa que cambie el alcance, no bloquean la primera entrega: despliegue público por Internet, autenticación OIDC/SSO, operación multiusuario remota, conciliación automática con brokers, órdenes de inversión, modelado fiscal completo, cobertura de todas las clases de instrumentos y automatización de correcciones financieras efectivas.

Esas funciones deben planificarse después de cerrar la operación local básica y no anunciarse como capacidades disponibles.

## 8. Evolución del producto: operación financiera asistida

La evolución posterior al MVP incorpora una **capa de operación financiera asistida**: el usuario podrá expresar una operación o una pregunta en lenguaje cotidiano y el sistema la traducirá a una acción o consulta estructurada dentro de los flujos financieros que ya existen.

No será un chatbot financiero autónomo ni un gestor genérico de gastos. Su diferencial será conectar una interacción simple con los datos y reglas reales del producto: préstamos, pagos, personas, aportes, inversiones y objetivos de reposición, sin crear una segunda fuente de verdad.

La capacidad se organiza en tres partes:

1. **Registro asistido:** interpretar una instrucción, resolver sus referencias contra personas, préstamos o planes existentes, preparar un borrador y mostrar la vista previa oficial. La confirmación humana será obligatoria; el registro seguirá utilizando el caso de uso financiero vigente, su idempotencia y su auditoría.
2. **Consulta financiera contextual:** permitir preguntas sobre capital colocado, cobros, vencimientos, rendimiento y brecha de reposición. Las respuestas se construirán con consultas oficiales de solo lectura, mostrarán fecha de corte y distinguirán hechos registrados, datos declarados y proyecciones.
3. **Seguimiento de reposición:** reunir en una vista el objetivo del plan, el capital inicial, los aportes y flujos registrados, las valuaciones declaradas y la brecha contra las referencias elegidas. Reutilizará los planes y reportes existentes; no creará una cartera paralela ni duplicará movimientos.

**Estado actual:** diseño de producto y contrato funcional documentados; no está implementado ni debe anunciarse como disponible. Su prioridad es posterior a la aceptación del MVP local y está coordinada por el [issue #370](https://github.com/JavierGrecco/prestamos_privados/issues/370).

El alcance, las reglas de interacción, la arquitectura prevista y los criterios de aceptación están en [Capacidad de operación financiera asistida](CAPACIDAD_OPERATIVA_ASISTIDA.md).

## 9. Evolución del producto: finanzas personales y capacidad de pago

La evolución F1 propone una sección de **Finanzas personales** para registrar ingresos, gastos, presupuestos, ahorros y compromisos que hoy no forman parte de los préstamos registrados. Su objetivo es que una persona conozca su margen mensual y pueda evaluar cómo cambia al asumir una nueva cuota.

La capacidad debe unir tres perspectivas sin confundirlas:

1. **Economía cotidiana:** ingresos netos, gastos esenciales y discrecionales, ahorro, reservas y movimientos reales.
2. **Compromisos actuales:** obligaciones externas declaradas y cuotas futuras de préstamos que la aplicación ya conoce.
3. **Nueva decisión:** cronograma oficial de la cuota candidata, saldo mensual resultante y escenarios de tensión durante todo el plazo.

La primera versión ya permite, desde **Mi espacio**, ingresar un margen libre mensual declarado, una cuota nueva y un colchón opcional. Muestra el remanente o faltante sin pedir sueldo ni registrar gastos, y no descuenta de nuevo las obligaciones actuales. El cálculo es temporal de sesión, solo ARS y de una cuota mensual representativa; no calcula DTI ni modifica préstamos. La funcionalidad está integrada mediante [PR #379](https://github.com/JavierGrecco/prestamos_privados/pull/379). La cuenta guiada, el registro detallado, la persistencia privada y los escenarios completos siguen pendientes.

La persona podrá empezar sin registrar gastos: ingresará cuánto dinero le queda libre al mes después de sus gastos y obligaciones actuales, antes de la nueva cuota. También podrá cargar totales sencillos o llevar un registro completo, si prefiere mayor detalle. El método y la calidad del dato se mostrarán siempre. El análisis mostrará ingresos recurrentes y variables por separado, presupuesto real frente a planificado, gastos anuales provisionados sin presentarlos como pagos mensuales, y meses en los que el saldo podría quedar en negativo. Para tarjetas y transferencias se deben definir reglas que eviten contar una compra y el pago del resumen como dos gastos, o una cuota interna como una deuda externa adicional.

La evaluación no se basará solo en el porcentaje de cuota sobre ingresos ni en un puntaje opaco. Debe explicar gastos esenciales, deuda total, ingreso residual, peor mes proyectado, reserva disponible, calidad de los datos y supuestos de cada escenario. La decisión final queda en la persona; no habrá aprobación o rechazo automático.

La información será privada por titular. El selector global de persona no dará acceso a datos personales ajenos y el rol ADMIN no tendrá lectura ordinaria automática del presupuesto. La primera etapa será local y con carga manual; importaciones bancarias, WhatsApp, OCR, voz y servicios externos quedan fuera hasta revisar seguridad y precisión. El permiso de aplicación tampoco equivale por sí mismo a cifrado de la base SQLite.

**Estado:** diseño de producto documentado en [FINANZAS_PERSONALES_CAPACIDAD_PAGO.md](FINANZAS_PERSONALES_CAPACIDAD_PAGO.md) y seguimiento en [issue #375](https://github.com/JavierGrecco/prestamos_privados/issues/375). Es trabajo Post-MVP, no una función implementada ni un cambio en las reglas vigentes. No debe retrasar la aceptación de #223.

## 10. Criterio de éxito del producto

El MVP se considera aceptado cuando una persona puede, sin scripts ni SQL manual:

- crear y consultar un préstamo de prueba bajo reglas aprobadas;
- verificar calendario, cuota, costo, pagos, mora, adelantos, participación e informe;
- crear, guardar, reabrir y exportar un plan interno de reposición;
- entender cuánto capital necesita reponer, qué referencia USD usa y cuál es su rendimiento alternativo objetivo;
- distinguir hechos, valuaciones, supuestos y proyecciones;
- verificar que pantalla, ledger y reportes concilian en la misma fecha de corte;
- instalar, reiniciar y restaurar una copia en otra ruta;
- consultar el historial y explicar por qué cambió un saldo.

La evidencia y los responsables de aceptación se registran en [issue #223](https://github.com/JavierGrecco/prestamos_privados/issues/223). Los criterios ordenados por fase están en el [roadmap operativo](ROADMAP_MVP_LOCAL.md).

## 11. Documentación funcional relacionada

- [M2 — Posición financiera](M2_POSICION_FINANCIERA.md)
- [M4 — Escenarios y planificación](M4_ESCENARIOS_PLANIFICACION.md)
- [M5 — Rendimiento explicado](M5_RENDIMIENTO_EXPLICADO.md)
- [M6 — Reportes personales](M6_REPORTES_PERSONALES.md)
- [M7 — Comparador de decisiones](M7_COMPARADOR_DECISIONES.md)
- [Principios de UX](PRINCIPIOS_UX.md)
- [Capacidad de operación financiera asistida](CAPACIDAD_OPERATIVA_ASISTIDA.md) — diseño posterior al MVP, sin implementación todavía
- [Arquitectura](ARCHITECTURE.md)
- [Instalación local](INSTALACION_LOCAL.md)
